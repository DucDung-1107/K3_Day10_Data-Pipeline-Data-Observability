from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from core.config import Settings
from core.utils import safe_slug, read_json, write_json


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse Crossref payload into a list of PaperRecord.

    Rules:
    - Unique paper_id generated using safe_slug(DOI)
    - Clean JATS/XML tags from abstract (summary)
    - Normalize dates to YYYY-MM-DD
    """
    items = payload.get("message", {}).get("items", [])
    records: list[PaperRecord] = []
    
    for item in items:
        # Extract DOI
        doi = item.get("DOI", "")
        if not doi:
            continue
        paper_id = safe_slug(doi)

        # Extract title
        title_list = item.get("title", [])
        title = ""
        if title_list and isinstance(title_list, list):
            title = str(title_list[0]).strip()
        if title:
            title = re.sub(r"<[^>]+>", "", title)
            title = re.sub(r"\s+", " ", title).strip()
        if not title:
            continue

        # Extract abstract and clean HTML/JATS XML tags
        abstract = item.get("abstract", "")
        if abstract:
            abstract = re.sub(r"<[^>]+>", "", abstract)
            abstract = re.sub(r"\s+", " ", abstract).strip()
        else:
            abstract = ""

        # Extract authors
        authors = []
        for aut in item.get("author", []):
            given = aut.get("given", "").strip()
            family = aut.get("family", "").strip()
            if given and family:
                name = f"{given} {family}"
            elif family:
                name = family
            else:
                name = given
            if name:
                authors.append(name)

        # Extract categories
        categories = item.get("subject", [])
        if not isinstance(categories, list):
            categories = []
        categories = [str(c).strip() for c in categories if c]

        primary_category = categories[0] if categories else "General"

        # Extract dates
        def extract_date(keys: list[str]) -> str | None:
            for key in keys:
                date_dict = item.get(key)
                if isinstance(date_dict, dict):
                    dp = date_dict.get("date-parts", [])
                    if dp and isinstance(dp, list) and len(dp) > 0 and isinstance(dp[0], list) and len(dp[0]) > 0:
                        parts = dp[0]
                        year = parts[0]
                        month = parts[1] if len(parts) > 1 else 1
                        day = parts[2] if len(parts) > 2 else 1
                        try:
                            return f"{year:04d}-{month:02d}-{day:02d}"
                        except Exception:
                            pass
            return None

        published = extract_date(["published-print", "published-online", "issued"])
        if not published:
            published = extract_date(["created"])
        if not published:
            published = "1970-01-01"

        updated = extract_date(["deposited", "indexed"])
        if not updated:
            updated = published

        # Extract URLs
        abs_url = item.get("URL", "")
        pdf_url = ""
        for link_item in item.get("link", []):
            url_str = link_item.get("URL", "")
            content_type = link_item.get("content-type", "")
            if content_type == "application/pdf" or ".pdf" in url_str.lower():
                pdf_url = url_str
                break
        if not pdf_url and item.get("link"):
            pdf_url = item["link"][0].get("URL", "")
        if not pdf_url:
            pdf_url = abs_url

        records.append(
            PaperRecord(
                paper_id=paper_id,
                title=title,
                summary=abstract,
                authors=authors,
                categories=categories,
                primary_category=primary_category,
                published=published,
                updated=updated,
                abs_url=abs_url,
                pdf_url=pdf_url,
                comment="",
            )
        )
    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Fetch Crossref records, cache raw response, parse, and save raw records."""
    import requests
    import time

    url = "https://api.crossref.org/works"
    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
    }
    headers = {
        "User-Agent": "PaperRAGPipeline/1.0 (mailto:agentic-retrieval@example.com)"
    }

    max_attempts = 5
    base_delay = 2.0
    response_json = None

    for attempt in range(max_attempts):
        try:
            response = requests.get(url, params=params, headers=headers, timeout=30)
            if response.status_code == 200:
                response_json = response.json()
                break
            elif response.status_code in (429, 503):
                delay = base_delay * (2 ** attempt)
                print(f"Received status code {response.status_code}. Retrying in {delay:.1f} seconds...")
                time.sleep(delay)
            else:
                response.raise_for_status()
        except requests.RequestException as e:
            if attempt == max_attempts - 1:
                raise
            delay = base_delay * (2 ** attempt)
            print(f"Request exception: {e}. Retrying in {delay:.1f} seconds...")
            time.sleep(delay)

    if response_json is None:
        raise RuntimeError("Failed to fetch records from Crossref after max retries.")

    # Save raw API response before parsing
    write_json(settings.paths.raw_api_response, response_json)

    # Parse raw payload
    records = parse_crossref_payload(response_json)

    # Save parsed records JSON
    records_dict_list = []
    for r in records:
        records_dict_list.append({
            "paper_id": r.paper_id,
            "title": r.title,
            "summary": r.summary,
            "authors": r.authors,
            "categories": r.categories,
            "primary_category": r.primary_category,
            "published": r.published,
            "updated": r.updated,
            "abs_url": r.abs_url,
            "pdf_url": r.pdf_url,
            "comment": r.comment,
        })
    write_json(settings.paths.raw_records_json, records_dict_list)

    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Load JSON snapshot and map to PaperRecord dataclasses."""
    data = read_json(path)
    records = []
    for item in data:
        records.append(
            PaperRecord(
                paper_id=item["paper_id"],
                title=item["title"],
                summary=item["summary"],
                authors=item["authors"],
                categories=item["categories"],
                primary_category=item["primary_category"],
                published=item["published"],
                updated=item["updated"],
                abs_url=item["abs_url"],
                pdf_url=item["pdf_url"],
                comment=item["comment"],
            )
        )
    return records

