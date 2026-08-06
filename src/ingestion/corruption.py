# =============================================================================
# Author: Quan123781 <quannguyen0442@gmail.com>
# Day 10 lab - Evaluation, Observability, Corruption & Integration
# =============================================================================
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Iterable

import pandas as pd

from core.utils import write_json

STALE_PUBLISHED_DATE = "2000-01-01"
NOISE_TEXT = (
    "qwerty zzzz 00000 lorem ipsum dolor sit amet unrelated filler tokens "
    "injected by the corruption step to dilute the semantic signal"
)
TRUNCATED_TITLE_CHARS = 12


def _rebuild_text_for_embedding(row: dict[str, Any]) -> str:
    """Reproduce the exact layout that `ingestion.cleaning` writes.

    Corruption has to leave the column in the same shape cleaning produces, otherwise the
    measured drop would come from a format mismatch rather than from the damaged data.
    """
    return (
        f"Title: {row['title']}\n"
        f"Authors: {row['authors_joined']}\n"
        f"Categories: {row['categories_joined']}\n"
        f"Summary: {row['summary']}"
    )


def _take(candidates: list[str], used: set[str], count: int) -> list[str]:
    picked: list[str] = []
    for paper_id in candidates:
        if len(picked) >= count:
            break
        if paper_id in used:
            continue
        picked.append(paper_id)
        used.add(paper_id)
    return picked


def _event(
    name: str,
    description: str,
    paper_ids: list[str],
    params: dict[str, Any],
    rows_before: int,
    rows_after: int,
    ground_truth_ids: set[str],
) -> dict[str, Any]:
    touched = sorted(set(paper_ids) & ground_truth_ids)
    return {
        "corruption": name,
        "description": description,
        "paper_ids": paper_ids,
        "parameters": params,
        "rows_before": rows_before,
        "rows_after": rows_after,
        "ground_truth_paper_ids_hit": touched,
        "hits_ground_truth": bool(touched),
    }


def corrupt_clean_dataframe(
    df: pd.DataFrame,
    output_log_path,
    target_paper_ids: Iterable[str] | None = None,
    run_date: datetime | None = None,
) -> pd.DataFrame:
    """Apply six controlled corruptions to a cleaned dataframe and log every change.

    `target_paper_ids` should be the ground-truth document IDs of the frozen test set.
    Corrupting papers the test set never asks about leaves every metric unchanged, so the
    scenarios below deliberately reach for those papers first.
    """
    if df.empty:
        raise ValueError("Cannot corrupt an empty cleaned dataframe.")

    run_date = run_date or datetime.now(UTC)
    ground_truth_ids = set(target_paper_ids or [])
    corrupted = df.copy().reset_index(drop=True)
    rows_before_all = len(corrupted)

    # Prefer papers the evaluator actually asks about, then fall back to the rest.
    order = [str(paper_id) for paper_id in corrupted["paper_id"]]
    priority = [paper_id for paper_id in order if paper_id in ground_truth_ids]
    fallback = [paper_id for paper_id in order if paper_id not in ground_truth_ids]
    used: set[str] = set()
    events: list[dict[str, Any]] = []

    def choose(from_priority: int = 1, from_fallback: int = 1) -> list[str]:
        return _take(priority, used, from_priority) + _take(fallback, used, from_fallback)

    def rows_for(paper_ids: list[str]) -> pd.Series:
        return corrupted["paper_id"].astype(str).isin(paper_ids)

    def refresh(mask: pd.Series) -> None:
        for index in corrupted.index[mask]:
            corrupted.at[index, "summary_chars"] = len(str(corrupted.at[index, "summary"]))
            corrupted.at[index, "text_for_embedding"] = _rebuild_text_for_embedding(
                corrupted.loc[index]
            )

    # 1. Drop the newest records: simulates an ingestion window that silently stopped.
    rows_before = len(corrupted)
    newest = corrupted.sort_values("published", ascending=False).head(2)
    dropped_ids = [str(paper_id) for paper_id in newest["paper_id"]]
    corrupted = corrupted[~rows_for(dropped_ids)].reset_index(drop=True)
    used.update(dropped_ids)
    events.append(
        _event(
            "drop_latest_records",
            "Removed the two most recently published papers from the dataset.",
            dropped_ids,
            {"count": len(dropped_ids), "selected_by": "published desc"},
            rows_before,
            len(corrupted),
            ground_truth_ids,
        )
    )

    # 2. Blank the summary: the field the summary questions are answered from.
    targets = choose()
    mask = rows_for(targets)
    rows_before = len(corrupted)
    corrupted.loc[mask, "summary"] = ""
    refresh(mask)
    events.append(
        _event(
            "blank_summary",
            "Emptied the summary field, leaving the row present but unanswerable.",
            targets,
            {"new_value": ""},
            rows_before,
            len(corrupted),
            ground_truth_ids,
        )
    )

    # 3. Inject noise: keeps the row populated but dilutes the embedding.
    targets = choose()
    mask = rows_for(targets)
    rows_before = len(corrupted)
    corrupted.loc[mask, "summary"] = corrupted.loc[mask, "summary"].astype(str) + " " + NOISE_TEXT
    refresh(mask)
    events.append(
        _event(
            "inject_noise",
            "Appended unrelated filler text to the summary and the embedding text.",
            targets,
            {"noise_chars": len(NOISE_TEXT)},
            rows_before,
            len(corrupted),
            ground_truth_ids,
        )
    )

    # 4. Truncate the title: breaks the exact-lookup path in `retrieval.qa`.
    targets = choose()
    mask = rows_for(targets)
    rows_before = len(corrupted)
    corrupted.loc[mask, "title"] = corrupted.loc[mask, "title"].astype(str).str[:TRUNCATED_TITLE_CHARS]
    refresh(mask)
    events.append(
        _event(
            "truncate_title",
            "Cut the title down to a stub so exact title lookup can no longer match.",
            targets,
            {"kept_chars": TRUNCATED_TITLE_CHARS},
            rows_before,
            len(corrupted),
            ground_truth_ids,
        )
    )

    # 5. Backdate the publication: the freshness signal should catch this one.
    targets = choose()
    mask = rows_for(targets)
    rows_before = len(corrupted)
    stale_age = (run_date.date() - datetime.strptime(STALE_PUBLISHED_DATE, "%Y-%m-%d").date()).days
    corrupted.loc[mask, "published"] = STALE_PUBLISHED_DATE
    corrupted.loc[mask, "age_days"] = stale_age
    events.append(
        _event(
            "stale_published_date",
            "Backdated the publication date so the row falls outside the freshness window.",
            targets,
            {"published": STALE_PUBLISHED_DATE, "age_days": stale_age},
            rows_before,
            len(corrupted),
            ground_truth_ids,
        )
    )

    # 6. Duplicate rows: the same paper now occupies several retrieval slots.
    targets = choose()
    rows_before = len(corrupted)
    duplicates = corrupted[rows_for(targets)].copy()
    corrupted = pd.concat([corrupted, duplicates], ignore_index=True)
    events.append(
        _event(
            "duplicate_rows",
            "Re-appended existing rows under the same paper_id.",
            targets,
            {"duplicated_rows": len(duplicates)},
            rows_before,
            len(corrupted),
            ground_truth_ids,
        )
    )

    touched = sorted({paper_id for event in events for paper_id in event["ground_truth_paper_ids_hit"]})
    log = {
        "generated_at": run_date.isoformat(timespec="seconds"),
        "rows_before": rows_before_all,
        "rows_after": len(corrupted),
        "ground_truth_paper_ids": sorted(ground_truth_ids),
        "ground_truth_paper_ids_touched": touched,
        "ground_truth_coverage": (
            round(len(touched) / len(ground_truth_ids), 4) if ground_truth_ids else None
        ),
        "corruptions": events,
    }
    write_json(output_log_path, log)
    print(f"Applied {len(events)} corruptions: {rows_before_all} -> {len(corrupted)} rows.")
    print(f"Ground-truth papers touched: {len(touched)}/{len(ground_truth_ids)}")
    if ground_truth_ids and not touched:
        print("WARNING: no ground-truth paper was corrupted; the metrics will not move.")
    print(f"Corruption log written to {output_log_path}")
    return corrupted
