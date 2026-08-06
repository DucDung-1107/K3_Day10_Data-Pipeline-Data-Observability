# =============================================================================
# Author: Nguyen Hai Quan - 2A202601863 <quannguyen0442@gmail.com>
# Day 10 lab - Evaluation, Observability, Corruption & Integration
# =============================================================================
from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.config import Settings
from core.utils import now_utc, write_json

REQUIRED_COLUMNS = (
    "paper_id",
    "title",
    "summary",
    "text_for_embedding",
    "published",
    "age_days",
)


def _check(name: str, passed: bool, observed: Any, expected: str, details: str) -> dict[str, Any]:
    return {
        "name": name,
        "status": "pass" if passed else "fail",
        "observed": observed,
        "expected": expected,
        "details": details,
    }


def _blank_count(df: pd.DataFrame, column: str) -> int:
    if column not in df.columns:
        return len(df)
    values = df[column].astype("string").fillna("")
    return int((values.str.strip() == "").sum())


def _summary_lengths(df: pd.DataFrame) -> pd.Series:
    if "summary_chars" in df.columns:
        return pd.to_numeric(df["summary_chars"], errors="coerce").fillna(0)
    if "summary" in df.columns:
        return df["summary"].astype("string").fillna("").str.len()
    return pd.Series(dtype="float64")


def _published_dates(df: pd.DataFrame) -> pd.Series:
    """Parse the `published` column, leaving anything unparseable as NaT.

    Cleaning normalises the column to YYYY-MM-DD, so the format is declared rather than
    inferred: a value that no longer matches is a data defect worth surfacing, not a
    parsing style to guess at.
    """
    if "published" not in df.columns:
        return pd.Series([pd.NaT] * len(df), dtype="datetime64[ns, UTC]")
    return pd.to_datetime(df["published"], errors="coerce", utc=True, format="ISO8601")


def _age_days(df: pd.DataFrame) -> pd.Series:
    if "age_days" in df.columns:
        return pd.to_numeric(df["age_days"], errors="coerce")
    if "published" in df.columns:
        return (pd.Timestamp(now_utc()) - _published_dates(df)).dt.days
    return pd.Series([pd.NA] * len(df), dtype="Float64")


def _resolve_report_path(settings: Settings, report_name: str) -> Path:
    name = Path(str(report_name)).name
    file_name = name if name.endswith(".json") else f"{name}.json"
    return settings.paths.quality_dir / file_name


def run_data_quality_checks(
    df: pd.DataFrame,
    settings: Settings,
    report_name: str,
    min_rows: int | None = None,
    # Cleaning drops any record whose summary is shorter than 100 characters, so a clean
    # dataset has none left. Anything shorter than this got past cleaning or was injected.
    min_summary_chars: int = 100,
) -> dict[str, Any]:
    """Run the data quality gate over a cleaned dataframe and persist the result.

    Every check reports what it observed so a failure can be traced back to rows in the
    dataset instead of being taken on trust.
    """
    # Retrieval asks for `top_k` documents, so a dataset smaller than that cannot even
    # fill one result page.
    threshold_rows = settings.top_k if min_rows is None else min_rows
    total_rows = int(len(df))
    checks: list[dict[str, Any]] = []

    missing_columns = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    checks.append(
        _check(
            "schema_columns_present",
            not missing_columns,
            "none" if not missing_columns else f"missing: {', '.join(missing_columns)}",
            "no missing column",
            f"Required: {', '.join(REQUIRED_COLUMNS)}. Missing columns break embedding, "
            "evaluation or freshness downstream.",
        )
    )

    checks.append(
        _check(
            "row_count_minimum",
            total_rows >= threshold_rows,
            total_rows,
            f">= {threshold_rows} rows",
            "A dataset smaller than top_k cannot return a full retrieval result set.",
        )
    )

    if "paper_id" in df.columns:
        null_ids = _blank_count(df, "paper_id")
        duplicate_ids = int(df["paper_id"].astype("string").fillna("").duplicated().sum())
        checks.append(
            _check(
                "paper_id_not_null",
                null_ids == 0,
                null_ids,
                "0 blank paper_id",
                "paper_id is the join key between raw, clean, index and ground truth.",
            )
        )
        checks.append(
            _check(
                "paper_id_unique",
                duplicate_ids == 0,
                duplicate_ids,
                "0 duplicate paper_id",
                "Duplicates inflate the corpus and let one paper occupy several top-k slots.",
            )
        )

    blank_titles = _blank_count(df, "title")
    checks.append(
        _check(
            "title_not_empty",
            blank_titles == 0,
            blank_titles,
            "0 blank titles",
            "The title drives exact lookup in the agent.",
        )
    )

    blank_embedding_text = _blank_count(df, "text_for_embedding")
    checks.append(
        _check(
            "text_for_embedding_not_empty",
            blank_embedding_text == 0,
            blank_embedding_text,
            "0 blank text_for_embedding",
            "An empty embedding text produces a document that can never be retrieved.",
        )
    )

    lengths = _summary_lengths(df)
    short_summaries = int((lengths < min_summary_chars).sum()) if len(lengths) else total_rows
    checks.append(
        _check(
            "summary_min_length",
            short_summaries == 0,
            short_summaries,
            f"0 rows below {min_summary_chars} characters",
            "Blank or truncated summaries are the corruption the agent notices first.",
        )
    )

    ages = _age_days(df)
    stale_rows = int((ages > settings.freshness_threshold_days).sum())
    unknown_age_rows = int(ages.isna().sum())
    checks.append(
        _check(
            "freshness_age_days",
            stale_rows == 0 and unknown_age_rows == 0,
            {"stale_rows": stale_rows, "unknown_age_rows": unknown_age_rows},
            f"0 rows older than {settings.freshness_threshold_days} days",
            "The source filter only requests recent papers, so any stale row is injected.",
        )
    )

    failed = [check for check in checks if check["status"] == "fail"]
    report_path = _resolve_report_path(settings, report_name)
    payload: dict[str, Any] = {
        "report_name": str(report_name),
        "generated_at": now_utc().isoformat(timespec="seconds"),
        "row_count": total_rows,
        "thresholds": {
            "min_rows": threshold_rows,
            "min_summary_chars": min_summary_chars,
            "freshness_threshold_days": settings.freshness_threshold_days,
        },
        "checks": checks,
        "total_checks": len(checks),
        "passed_checks": len(checks) - len(failed),
        "failed_checks": len(failed),
        "failed_check_names": [check["name"] for check in failed],
        "success": not failed,
        "report_path": str(report_path),
    }
    write_json(report_path, payload)
    return payload


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Summarise how recent the dataset is and persist the payload as JSON."""
    total_rows = int(len(df))
    threshold = settings.freshness_threshold_days

    published = _published_dates(df)
    ages = _age_days(df)
    stale_rows = int((ages > threshold).sum())
    unknown_age_rows = int(ages.isna().sum())
    fresh_rows = total_rows - stale_rows - unknown_age_rows

    def _as_date(value: Any) -> str | None:
        return None if pd.isna(value) else value.date().isoformat()

    def _as_int(value: Any) -> int | None:
        return None if pd.isna(value) else int(value)

    payload: dict[str, Any] = {
        "generated_at": now_utc().isoformat(timespec="seconds"),
        "threshold_days": threshold,
        "total_rows": total_rows,
        "latest_published": _as_date(published.max()) if total_rows else None,
        "oldest_published": _as_date(published.min()) if total_rows else None,
        "fresh_rows": fresh_rows,
        "stale_rows": stale_rows,
        "unknown_age_rows": unknown_age_rows,
        "stale_ratio": round(stale_rows / total_rows, 4) if total_rows else None,
        "min_age_days": _as_int(ages.min()) if total_rows else None,
        "median_age_days": _as_int(ages.median()) if total_rows else None,
        "max_age_days": _as_int(ages.max()) if total_rows else None,
        # The source filter requests papers published within the threshold window, so a
        # clean dataset has no stale row at all. Any stale row was introduced later.
        "is_fresh": total_rows > 0 and stale_rows == 0 and unknown_age_rows == 0,
        "report_path": str(report_path),
    }
    write_json(report_path, payload)
    return payload
