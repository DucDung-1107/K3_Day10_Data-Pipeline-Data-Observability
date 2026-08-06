from __future__ import annotations

from datetime import datetime
import pandas as pd

from ingestion.crossref import PaperRecord


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw records into a structured pandas DataFrame ready for embedding.

    Rules:
    - Normalizes title, summary, authors, categories
    - Parses published dates and computes age_days
    - Deduplicates records by paper_id (keeps latest & most complete)
    - Constructs text_for_embedding helper column
    """
    cleaned_rows = []

    dropped_missing_title = 0
    dropped_missing_summary = 0
    dropped_invalid_date = 0

    for r in records:
        # Validate critical fields
        if not r.title or not r.title.strip():
            dropped_missing_title += 1
            continue

        if not r.summary or not r.summary.strip():
            dropped_missing_summary += 1
            continue

        # Parse published date and compute age_days
        try:
            pub_date = datetime.strptime(r.published, "%Y-%m-%d")
        except ValueError:
            dropped_invalid_date += 1
            continue

        # Compute age_days relative to run_date
        age_days = (run_date.date() - pub_date.date()).days
        if age_days < 0:
            age_days = 0

        # Normalization
        title_clean = r.title.strip()
        summary_clean = r.summary.strip()

        # Authors handling
        authors_list = [a.strip() for a in r.authors if a.strip()]
        if not authors_list:
            authors_list = ["Unknown"]
        authors_joined = ", ".join(authors_list)

        # Categories handling
        categories_list = [c.strip() for c in r.categories if c.strip()]
        if not categories_list:
            categories_list = ["General"]
        categories_joined = ", ".join(categories_list)

        primary_cat = categories_list[0] if categories_list else "General"
        summary_chars = len(summary_clean)

        # Build text_for_embedding
        text_for_embedding = (
            f"Title: {title_clean}\n"
            f"Authors: {authors_joined}\n"
            f"Categories: {categories_joined}\n"
            f"Summary: {summary_clean}"
        )

        cleaned_rows.append({
            "paper_id": r.paper_id,
            "title": title_clean,
            "summary": summary_clean,
            "authors": authors_list,
            "authors_joined": authors_joined,
            "categories": categories_list,
            "categories_joined": categories_joined,
            "primary_category": primary_cat,
            "published": r.published,
            "updated": r.updated,
            "age_days": age_days,
            "abs_url": r.abs_url,
            "pdf_url": r.pdf_url,
            "comment": r.comment,
            "summary_chars": summary_chars,
            "text_for_embedding": text_for_embedding,
        })

    df = pd.DataFrame(cleaned_rows)

    if df.empty:
        print("Warning: Cleaned DataFrame is empty.")
        return df

    # Deduplicate by paper_id (which is safe_slug(DOI)).
    # Sort to prioritize keeping the record with the most recent updated date and longest summary length.
    total_before_dedupe = len(df)
    df = df.sort_values(by=["updated", "summary_chars"], ascending=[False, False])
    df = df.drop_duplicates(subset=["paper_id"], keep="first")
    dropped_duplicates = total_before_dedupe - len(df)

    # Sort results chronologically descending
    df = df.sort_values(by="published", ascending=False).reset_index(drop=True)

    print("--- Cleaning Audit Log ---")
    print(f"Total raw records input: {len(records)}")
    print(f"Dropped due to missing title: {dropped_missing_title}")
    print(f"Dropped due to missing abstract: {dropped_missing_summary}")
    print(f"Dropped due to invalid date format: {dropped_invalid_date}")
    print(f"Dropped as duplicate papers: {dropped_duplicates}")
    print(f"Total cleaned records output: {len(df)}")
    print("--------------------------")

    return df

