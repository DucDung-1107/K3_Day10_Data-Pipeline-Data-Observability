from __future__ import annotations

import dataclasses
from datetime import datetime, UTC
import pandas as pd

from core.config import load_settings
from ingestion.crossref import fetch_source_records, load_raw_records
from ingestion.cleaning import build_clean_dataframe
from retrieval.index import LocalEmbeddingIndex
from evaluation.testset import build_test_set
from evaluation.metrics import evaluate_pipeline
from observability.quality import run_data_quality_checks, build_freshness_report
from observability.reporting import generate_phase1_report


def validate_clean_schema(df: pd.DataFrame) -> None:
    """Mục 3: Đảm bảo Schema ổn định trước khi đi tiếp"""
    expected_columns = {"id", "title", "abstract"} 
    missing_cols = expected_columns - set(df.columns)
    if missing_cols:
        raise ValueError(f"Blocker: Clean Schema không ổn định! Thiếu các cột bắt buộc: {missing_cols}")

def main() -> None:
    # 1. Load settings
    print("Loading settings...")
    settings = load_settings()
    
    # 2. Load or fetch raw records (Avoid redundant fetches)
    raw_records_path = settings.paths.raw_records_json
    should_fetch = settings.refresh_source or not raw_records_path.exists()
    
    if should_fetch:
        print("Fetching raw records from Crossref API...")
        records = fetch_source_records(settings)
        print(f"Fetched {len(records)} raw records.")
    else:
        print(f"Loading raw records from cache: {raw_records_path}")
        records = load_raw_records(raw_records_path)
        print(f"Loaded {len(records)} raw records.")
        
    raw_count = len(records)
        
    # 3. Clean records
    run_date = datetime.now(UTC)
    print(f"Running cleaning pipeline with run_date = {run_date}...")
    df = build_clean_dataframe(records, run_date)
    clean_count = len(df)
    
    # --- MỤC 1 & 2: KIỂM TRA ĐIỀU KIỆN DỪNG VÀ HAO HỤT DỮ LIỆU ---
    print(f"   -> Raw count: {raw_count} | Clean count: {clean_count}")
    
    # Điều kiện dừng 1 (Mục 1)
    if clean_count == 0:
        raise ValueError("Blocker: Tập dữ liệu trống sau khi làm sạch. Dừng pipeline!")
    
    # Điều kiện dừng 2 (Mục 2): Bất thường hao hụt (Ví dụ: mất quá 80% dữ liệu)
    drop_rate = (raw_count - clean_count) / raw_count
    if drop_rate > 0.8:
        raise RuntimeError(f"Blocker: Hao hụt dữ liệu bất thường! "
                           f"Raw: {raw_count}, Clean: {clean_count}. Drop rate: {drop_rate:.1%}")
                           
    # --- MỤC 3: KIỂM TRA SCHEMA TRƯỚC KHI INDEX ---
    validate_clean_schema(df)
    print("   -> Schema hợp lệ, sẵn sàng cho RAG!")

    # Save cleaned files
    print(f"Saving cleaned CSV to {settings.paths.clean_csv}")
    settings.paths.clean_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(settings.paths.clean_csv, index=False)
    
    print(f"Saving cleaned JSON to {settings.paths.clean_json}")
    settings.paths.clean_json.parent.mkdir(parents=True, exist_ok=True)
    df.to_json(settings.paths.clean_json, orient="records", indent=2)
    
    # 4. Build Chroma vector index
    print("Building Chroma baseline index...")
    index = LocalEmbeddingIndex.build(df, settings, settings.paths.embeddings_json)
    print(f"Index built with collection: {index.collection_name}")
    
    # 5. Generate evaluation test set
    test_set_path = settings.paths.eval_testset
    should_build_test_set = settings.refresh_test_set or not test_set_path.exists()
    if should_build_test_set:
        print(f"Building evaluation test set at {test_set_path}...")
        build_test_set(df, test_set_path)
    else:
        print(f"Using existing test set from {test_set_path}")
        
    # 6. Evaluate pipeline
    print("Evaluating pipeline on test set...")
    override_settings = settings
    if not settings.google_api_key and settings.openai_api_key:
        print("GOOGLE_API_KEY is empty. Overriding provider to 'openai' for evaluation.")
        override_settings = dataclasses.replace(
            settings,
            llm_provider="openai",
            model_name="gpt-4o-mini"
        )
        
    bundle = evaluate_pipeline(
        settings=override_settings,
        index=index,
        test_set_path=test_set_path,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers
    )
    print(f"Evaluation finished. Summary metrics: {bundle.summary}")
    
    # 7. Run data quality checks & freshness reports
    print("Running data quality checks...")
    quality_results = run_data_quality_checks(df, settings, "baseline_quality")
    
    print("Building freshness report...")
    freshness_results = build_freshness_report(df, settings, settings.paths.freshness_report)
    
    # 8. Generate markdown report
    source_summary = {
        "source_api": settings.source_api,
        "query": settings.source_query,
        "filter": settings.source_filter,
        "raw_records": len(records)
    }
    print(f"Generating Phase 1 baseline report at {settings.paths.baseline_report}...")
    generate_phase1_report(
        report_path=settings.paths.baseline_report,
        source_summary=source_summary,
        metrics=bundle.summary,
        quality=quality_results,
        freshness=freshness_results
    )
    
    print("Hoàn thành Pipeline Phase 1!")


if __name__ == "__main__":
    main()
