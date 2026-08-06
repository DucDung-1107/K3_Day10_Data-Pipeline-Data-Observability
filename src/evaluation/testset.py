# =============================================================================
# Author: Quan123781 <quannguyen0442@gmail.com>
# Day 10 lab - Evaluation, Observability, Corruption & Integration
# =============================================================================
from __future__ import annotations

from typing import Any

import pandas as pd

from core.utils import first_sentence, normalize_whitespace, safe_slug, write_json

REQUIRED_COLUMNS = (
    "paper_id",
    "title",
    "summary",
    "authors_joined",
    "categories_joined",
    "published",
)

# `retrieval.qa._extract_answer` routes a question to a metadata field by matching these
# phrases against the lowercased question. A question must contain exactly one of them
# (or none, for the summary fallback), otherwise the extracted answer is taken from a
# different field than the ground truth recorded here and every score becomes noise.
ROUTER_PHRASES = (
    "who authored",
    "list the authors",
    "when was",
    "publication date",
    "published on",
    "what categories",
)

QUESTION_TEMPLATES: dict[str, str] = {
    "summary": "What is the paper '{title}' about?",
    "authors": "Who authored the paper '{title}'?",
    "date": "When was the paper '{title}' published?",
    "categories": "What categories are assigned to the paper '{title}'?",
}


def _text(value: Any) -> str:
    if value is None:
        return ""
    return normalize_whitespace(str(value))


def _ground_truth(question_type: str, row: dict[str, Any]) -> str:
    """Mirror `retrieval.qa._extract_answer` so a correct retrieval scores a perfect match."""
    if question_type == "authors":
        return _text(row["authors_joined"])
    if question_type == "date":
        return _text(row["published"])
    if question_type == "categories":
        return _text(row["categories_joined"])
    return first_sentence(str(row["summary"]))


def _is_eligible(row: dict[str, Any]) -> bool:
    if any(not _text(row.get(column)) for column in REQUIRED_COLUMNS):
        return False

    title = _text(row["title"])
    # `answer_question` extracts the exact-lookup key with r"'([^']+)'", so an apostrophe
    # inside the title would truncate the key and break the lookup.
    if "'" in title:
        return False
    return not any(phrase in title.lower() for phrase in ROUTER_PHRASES)


def _select_papers(df: pd.DataFrame, max_papers: int) -> list[dict[str, Any]]:
    seen_titles: set[str] = set()
    eligible: list[dict[str, Any]] = []
    for row in df.to_dict(orient="records"):
        if not _is_eligible(row):
            continue
        title_key = _text(row["title"]).lower()
        if title_key in seen_titles:
            continue
        seen_titles.add(title_key)
        eligible.append(row)

    # Sort then sample at a fixed stride: the same cleaned dataset always yields the same
    # test set, which is what makes baseline/corrupted/repaired comparable.
    eligible.sort(key=lambda row: str(row["paper_id"]))
    if len(eligible) <= max_papers:
        return eligible
    stride = len(eligible) / max_papers
    return [eligible[int(index * stride)] for index in range(max_papers)]


def build_test_set(df: pd.DataFrame, output_path, max_papers: int = 6) -> list[dict[str, Any]]:
    """Build the evaluation set from the cleaned dataframe and persist it as JSON.

    The test set is written once and reused unchanged for the baseline, corrupted and
    repaired runs; regenerating it between runs would invalidate every comparison.
    """
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing_columns:
        raise ValueError(f"Cleaned dataframe is missing required columns: {', '.join(missing_columns)}")
    if len(df) < 4:
        raise ValueError(f"Need at least 4 cleaned documents to build a test set, got {len(df)}.")

    papers = _select_papers(df, max_papers)
    if not papers:
        raise ValueError(
            "No cleaned row is eligible for the test set. Every row is missing one of "
            f"{', '.join(REQUIRED_COLUMNS)} or has a title that breaks exact lookup."
        )

    test_set: list[dict[str, Any]] = []
    for row in papers:
        paper_id = str(row["paper_id"])
        title = _text(row["title"])
        for question_type, template in QUESTION_TEMPLATES.items():
            ground_truth = _ground_truth(question_type, row)
            if not ground_truth:
                continue
            test_set.append(
                {
                    "id": f"{question_type}-{safe_slug(paper_id)}",
                    "question_type": question_type,
                    "question": template.format(title=title),
                    "ground_truth": ground_truth,
                    "ground_truth_doc_ids": [paper_id],
                }
            )

    write_json(output_path, test_set)
    return test_set
