from __future__ import annotations

import dataclasses
from datetime import datetime, UTC
import pandas as pd
from pathlib import Path

from core.config import load_settings
from core.utils import read_json
from ingestion.crossref import load_raw_records
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from retrieval.index import LocalEmbeddingIndex
from evaluation.metrics import evaluate_pipeline
from observability.quality import run_data_quality_checks, build_freshness_report
from observability.reporting import generate_corruption_report


def main() -> None:
    print("Loading settings...")
    settings = load_settings()

    # --- CP5 Task 1: Verify raw source is intact before corruption ---
    print("\n--- CP5 Task 1: Raw Source Integrity Check ---")
    raw_records_path = settings.paths.raw_records_json
    if not raw_records_path.exists():
        raise FileNotFoundError(f"Raw records cache not found at {raw_records_path}. Run phase 1 first.")
    raw_records = load_raw_records(raw_records_path)
    print(f"Verified: Raw records cache is intact and contains {len(raw_records)} records.")

    # --- CP5 Task 2: Choose target record with clear lineage for repair ---
    print("\n--- CP5 Task 2: Lineage Target Selection ---")
    target_paper_id = "10-2118-234689-pa"
    # Verify target paper exists in raw records
    target_in_raw = any(r.paper_id == target_paper_id for r in raw_records)
    print(f"Target selected: '{target_paper_id}' (SafeRAG paper). In raw records: {target_in_raw}")

    # --- CP5 Task 3: Ensure no new source fetches are performed ---
    print("\n--- CP5 Task 3: Fetching Constraint Check ---")
    print(f"Checking Settings: refresh_source = {settings.refresh_source}")
    if settings.refresh_source:
        print("Warning: refresh_source is set to True. Forcing to False to keep evaluation fair.")
        settings = dataclasses.replace(settings, refresh_source=False)
    print("Confirmed: Pipeline will read exclusively from cached snapshots.")

    # 1. Load baseline metrics and clean baseline dataset
    print("\nLoading baseline clean data...")
    clean_json_path = settings.paths.clean_json
    df_baseline = pd.read_json(clean_json_path)
    print(f"Loaded baseline clean dataset containing {len(df_baseline)} records.")
    
    baseline_metrics_path = settings.paths.baseline_metrics
    baseline_metrics = read_json(baseline_metrics_path)

    # 2. Create corrupted dataframe (CP5 Tasks 4 & 5)
    print("\n--- CP5 Tasks 4 & 5: Corrupting DataFrame & Logging ---")
    df_corrupted = corrupt_clean_dataframe(df_baseline, settings.paths.corruption_log)

    # --- CP5 Task 6: Validate corrupted dataset against baseline and log ---
    print("\n--- CP5 Task 6: Verifying Corrupted Dataset Divergence ---")
    corruption_logs = read_json(settings.paths.corruption_log)
    print(f"Read {len(corruption_logs)} corruption log actions.")
    
    # Assert count changes match drops/duplicates
    dropped_ids = [log["paper_id"] for log in corruption_logs if log["type"] == "drop_latest"]
    duplicated_ids = [log["paper_id"] for log in corruption_logs if log["type"] == "duplicate"]
    
    # Confirm dropped records are missing from corrupted df
    for paper_id in dropped_ids:
        assert paper_id not in df_corrupted["paper_id"].values, f"Dropped record {paper_id} is still in corrupted DF!"
    print(f"Verified: Latest records {dropped_ids} were successfully dropped.")

    # Confirm duplicate records exist
    for paper_id in duplicated_ids:
        matches = df_corrupted[df_corrupted["paper_id"] == paper_id]
        assert len(matches) > 1, f"Duplicated record {paper_id} was not duplicated!"
    print(f"Verified: Duplicate records {duplicated_ids} are present.")

    # 3. Save corrupted artifacts
    print(f"Saving corrupted CSV to {settings.paths.corrupted_clean_csv}")
    settings.paths.corrupted_clean_csv.parent.mkdir(parents=True, exist_ok=True)
    df_corrupted.to_csv(settings.paths.corrupted_clean_csv, index=False)
    
    print(f"Saving corrupted JSON to {settings.paths.corrupted_clean_json}")
    settings.paths.corrupted_clean_json.parent.mkdir(parents=True, exist_ok=True)
    df_corrupted.to_json(settings.paths.corrupted_clean_json, orient="records", indent=2)

    # 4. Rebuild index and evaluate corrupted dataset
    print("\nBuilding Chroma corrupted index...")
    index_corrupted = LocalEmbeddingIndex.build(df_corrupted, settings, settings.paths.corrupted_embeddings_json)
    print(f"Corrupted index built with collection: {index_corrupted.collection_name}")

    print("Evaluating corrupted RAG pipeline...")
    override_settings = settings
    if not settings.google_api_key and settings.openai_api_key:
        override_settings = dataclasses.replace(
            settings,
            llm_provider="openai",
            model_name="gpt-4o-mini"
        )
        
    corrupted_metrics_results = evaluate_pipeline(
        settings=override_settings,
        index=index_corrupted,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.corrupted_metrics,
        answers_output_path=settings.paths.corrupted_answers
    )
    print(f"Corrupted evaluation metrics: {corrupted_metrics_results.summary}")

    # 5. Run quality checks & freshness report on corrupted dataset
    print("Running data quality checks on corrupted dataset...")
    corrupted_quality = run_data_quality_checks(df_corrupted, settings, "corrupted_quality")
    
    print("Building freshness report on corrupted dataset...")
    corrupted_freshness_path = settings.paths.quality_dir / "corrupted_freshness.json"
    corrupted_freshness = build_freshness_report(df_corrupted, settings, corrupted_freshness_path)

    # 6. Repair phase: rebuild from cached raw records (CP6)
    print("\n--- Repair Phase: Restoring Clean Dataset from Source ---")
    run_date = datetime.now(UTC)
    df_repaired = build_clean_dataframe(raw_records, run_date)
    
    # Save repaired artifacts
    print(f"Saving repaired CSV to {settings.paths.repaired_clean_csv}")
    df_repaired.to_csv(settings.paths.repaired_clean_csv, index=False)
    print(f"Saving repaired JSON to {settings.paths.repaired_clean_json}")
    df_repaired.to_json(settings.paths.repaired_clean_json, orient="records", indent=2)

    # 7. Rebuild index and evaluate repaired dataset
    print("\nBuilding Chroma repaired index...")
    index_repaired = LocalEmbeddingIndex.build(df_repaired, settings, settings.paths.repaired_embeddings_json)
    print(f"Repaired index built with collection: {index_repaired.collection_name}")

    print("Evaluating repaired RAG pipeline...")
    repaired_metrics_results = evaluate_pipeline(
        settings=override_settings,
        index=index_repaired,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.repaired_metrics,
        answers_output_path=settings.paths.repaired_answers
    )
    print(f"Repaired evaluation metrics: {repaired_metrics_results.summary}")

    # Run quality checks & freshness report on repaired dataset
    print("Running data quality checks on repaired dataset...")
    repaired_quality = run_data_quality_checks(df_repaired, settings, "repaired_quality")
    
    print("Building freshness report on repaired dataset...")
    repaired_freshness_path = settings.paths.quality_dir / "repaired_freshness.json"
    repaired_freshness = build_freshness_report(df_repaired, settings, repaired_freshness_path)

    # 8. Generate comparison report
    print(f"\nGenerating comparison report at {settings.paths.comparison_report}...")
    generate_corruption_report(
        report_path=settings.paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_metrics_results.summary,
        repaired_metrics=repaired_metrics_results.summary,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness
    )
    print("Hoàn thành Pipeline Corruption Flow!")


if __name__ == "__main__":
    main()

