from __future__ import annotations

from datetime import datetime, UTC
from pathlib import Path
from typing import Any
import pandas as pd

from core.config import Settings
from core.utils import write_json


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Execute quality checks on the cleaned dataframe and log results to data/quality."""
    total_rows = len(df)
    missing_titles = int(df["title"].isnull().sum() + (df["title"] == "").sum())
    missing_summaries = int(df["summary"].isnull().sum() + (df["summary"] == "").sum())
    duplicate_ids = int(df.duplicated(subset=["paper_id"]).sum())
    short_summaries = int((df["summary"].str.len() < 100).sum())
    negative_ages = int((df["age_days"] < 0).sum())

    # Verify quality thresholds
    has_rows = total_rows > 0
    no_missing_titles = missing_titles == 0
    no_missing_summaries = missing_summaries == 0
    no_duplicates = duplicate_ids == 0
    no_short_summaries = short_summaries == 0
    no_negative_ages = negative_ages == 0

    success = (
        has_rows
        and no_missing_titles
        and no_missing_summaries
        and no_duplicates
        and no_short_summaries
        and no_negative_ages
    )

    results = {
        "report_name": report_name,
        "timestamp": datetime.now(UTC).isoformat(),
        "success": success,
        "metrics": {
            "total_rows": total_rows,
            "missing_titles": missing_titles,
            "missing_summaries": missing_summaries,
            "duplicate_ids": duplicate_ids,
            "short_summaries": short_summaries,
            "negative_ages": negative_ages,
        },
        "checks": {
            "has_rows": has_rows,
            "no_missing_titles": no_missing_titles,
            "no_missing_summaries": no_missing_summaries,
            "no_duplicates": no_duplicates,
            "no_short_summaries": no_short_summaries,
            "no_negative_ages": no_negative_ages,
        }
    }

    report_path = settings.paths.quality_dir / f"{report_name}.json"
    write_json(report_path, results)
    print(f"Data quality checks completed. Success: {success}. Saved report to {report_path}")
    return results


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Compile freshness report from published date and age_days field."""
    if df.empty:
        results = {
            "timestamp": datetime.now(UTC).isoformat(),
            "latest_published": "N/A",
            "oldest_published": "N/A",
            "stale_rows": 0,
            "total_rows": 0,
            "is_fresh": False,
            "reason": "DataFrame is empty.",
            "threshold_days": settings.freshness_threshold_days,
        }
        write_json(Path(report_path), results)
        return results

    latest_published = df["published"].max()
    oldest_published = df["published"].min()
    
    threshold = settings.freshness_threshold_days
    stale_rows_mask = df["age_days"] > threshold
    stale_rows = int(stale_rows_mask.sum())
    total_rows = len(df)
    
    is_fresh = stale_rows == 0

    results = {
        "timestamp": datetime.now(UTC).isoformat(),
        "latest_published": str(latest_published),
        "oldest_published": str(oldest_published),
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "is_fresh": is_fresh,
        "threshold_days": threshold,
    }

    write_json(Path(report_path), results)
    print(f"Freshness report built. Is fresh: {is_fresh}. Saved to {report_path}")
    return results

