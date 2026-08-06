from __future__ import annotations

import json
from pathlib import Path
import pandas as pd
import datetime as dt

from core.utils import write_json


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    """Simulate various forms of data corruption and save a log.

    Simulations:
    1. Drop latest 3 records (simulate missing recent data)
    2. Set summary to empty string for 2 rows (simulate incomplete data)
    3. Inject random noise into summary for 2 rows (simulate text corruption)
    4. Truncate title to first 10 characters for 2 rows (simulate bad extraction)
    5. Make publication date stale (2020-01-01) for 2 rows (simulate stale data)
    6. Add duplicate rows for 2 records (simulate duplicates)
    """
    corrupted_df = df.copy()
    logs = []
    
    # Sort descending by published date to easily identify latest
    corrupted_df = corrupted_df.sort_values(by="published", ascending=False).reset_index(drop=True)
    before_count = len(corrupted_df)

    # 1. Drop top 3 latest records
    dropped_rows = corrupted_df.head(3)
    corrupted_df = corrupted_df.iloc[3:].reset_index(drop=True)
    after_count = len(corrupted_df)
    
    for _, row in dropped_rows.iterrows():
        logs.append({
            "paper_id": row["paper_id"],
            "type": "drop_latest",
            "parameter": {
                "original_title": row["title"],
                "original_published": row["published"]
            },
            "before_count": before_count,
            "after_count": after_count
        })
    before_count = after_count

    # 2. Blank summary (index 0 and 1)
    for idx in [0, 1]:
        if idx < len(corrupted_df):
            old_summary = corrupted_df.loc[idx, "summary"]
            paper_id = corrupted_df.loc[idx, "paper_id"]
            corrupted_df.loc[idx, "summary"] = ""
            logs.append({
                "paper_id": paper_id,
                "type": "blank_summary",
                "parameter": {
                    "original_summary_len": len(old_summary),
                    "new_summary": ""
                },
                "before_count": before_count,
                "after_count": before_count
            })

    # 3. Inject noise into summary (index 2 and 3)
    for idx in [2, 3]:
        if idx < len(corrupted_df):
            old_summary = corrupted_df.loc[idx, "summary"]
            paper_id = corrupted_df.loc[idx, "paper_id"]
            noise_text = " [CORRUPTED_NOISE_ERROR_404_GARBAGE] " * 3
            corrupted_df.loc[idx, "summary"] = old_summary + noise_text
            logs.append({
                "paper_id": paper_id,
                "type": "inject_noise",
                "parameter": {
                    "original_len": len(old_summary),
                    "noise_injected": noise_text
                },
                "before_count": before_count,
                "after_count": before_count
            })

    # 4. Truncate title (index 4 and 5)
    for idx in [4, 5]:
        if idx < len(corrupted_df):
            old_title = corrupted_df.loc[idx, "title"]
            paper_id = corrupted_df.loc[idx, "paper_id"]
            new_title = old_title[:10] + "..."
            corrupted_df.loc[idx, "title"] = new_title
            logs.append({
                "paper_id": paper_id,
                "type": "truncate_title",
                "parameter": {
                    "original_title": old_title,
                    "new_title": new_title
                },
                "before_count": before_count,
                "after_count": before_count
            })

    # 5. Stale published date (index 6 and 7)
    for idx in [6, 7]:
        if idx < len(corrupted_df):
            old_date = corrupted_df.loc[idx, "published"]
            paper_id = corrupted_df.loc[idx, "paper_id"]
            new_date = "2020-01-01"
            corrupted_df.loc[idx, "published"] = new_date
            logs.append({
                "paper_id": paper_id,
                "type": "stale_date",
                "parameter": {
                    "original_date": old_date,
                    "new_date": new_date
                },
                "before_count": before_count,
                "after_count": before_count
            })

    # 6. Add duplicate rows (index 8 and 9)
    duplicates_to_add = []
    for idx in [8, 9]:
        if idx < len(corrupted_df):
            row_to_dup = corrupted_df.iloc[idx].copy()
            duplicates_to_add.append(row_to_dup)
            
    if duplicates_to_add:
        dup_df = pd.DataFrame(duplicates_to_add)
        corrupted_df = pd.concat([corrupted_df, dup_df], ignore_index=True)
        after_count = len(corrupted_df)
        for row in duplicates_to_add:
            logs.append({
                "paper_id": row["paper_id"],
                "type": "duplicate",
                "parameter": {
                    "title": row["title"]
                },
                "before_count": before_count,
                "after_count": after_count
            })
        before_count = after_count

    # 7. Rebuild text_for_embedding, age_days, id, abstract
    corrupted_df["summary_chars"] = corrupted_df["summary"].str.len()
    corrupted_df["text_for_embedding"] = (
        "Title: " + corrupted_df["title"] + "\n" +
        "Authors: " + corrupted_df["authors_joined"] + "\n" +
        "Categories: " + corrupted_df["categories_joined"] + "\n" +
        "Summary: " + corrupted_df["summary"]
    )
    
    # Recalculate age_days from a reference date representing today (2026-08-06)
    ref_date = dt.date(2026, 8, 6)
    new_ages = []
    for pub_str in corrupted_df["published"]:
        try:
            p_date = dt.datetime.strptime(pub_str, "%Y-%m-%d").date()
            age = (ref_date - p_date).days
            new_ages.append(max(0, age))
        except Exception:
            new_ages.append(181)
    corrupted_df["age_days"] = new_ages

    # Populate compatibility copy columns
    corrupted_df["id"] = corrupted_df["paper_id"]
    corrupted_df["abstract"] = corrupted_df["summary"]

    # 8. Save corruption log
    Path(output_log_path).parent.mkdir(parents=True, exist_ok=True)
    write_json(Path(output_log_path), logs)
    
    print(f"Data corruption completed. Logged {len(logs)} actions to {output_log_path}")
    return corrupted_df

