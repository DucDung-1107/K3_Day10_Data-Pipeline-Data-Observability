import sys
from pathlib import Path

# Add src to python path
sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from core.config import load_settings
from ingestion.crossref import fetch_source_records, load_raw_records
from ingestion.cleaning import build_clean_dataframe
from datetime import datetime, UTC
from core.utils import ensure_parent

def main():
    settings = load_settings()
    
    # 1. Check if raw records file exists
    raw_records_path = settings.paths.raw_records_json
    
    # Determine if we need to fetch
    should_fetch = settings.refresh_source or not raw_records_path.exists()
    
    if should_fetch:
        print("Fetching raw records from Crossref API...")
        try:
            records = fetch_source_records(settings)
            print(f"Fetched {len(records)} raw records.")
        except Exception as e:
            print(f"Error fetching from API: {e}")
            sys.exit(1)
    else:
        print(f"Loading raw records from cache: {raw_records_path}")
        records = load_raw_records(raw_records_path)
        print(f"Loaded {len(records)} raw records.")
        
    # 2. Clean records
    run_date = datetime.now(UTC)
    print(f"Running cleaning pipeline with run_date = {run_date}...")
    df = build_clean_dataframe(records, run_date)
    
    if df.empty:
        print("Error: Cleaned dataframe is empty.")
        sys.exit(1)
        
    # 3. Save cleaned data to paths specified in Settings
    print(f"Saving cleaned CSV to {settings.paths.clean_csv}")
    ensure_parent(settings.paths.clean_csv)
    df.to_csv(settings.paths.clean_csv, index=False)
    
    print(f"Saving cleaned JSON to {settings.paths.clean_json}")
    ensure_parent(settings.paths.clean_json)
    df.to_json(settings.paths.clean_json, orient="records", indent=2)
    
    # 4. Perform diagnostic validations
    print("\n=== Validation Checks ===")
    
    # Check paper_id uniqueness
    is_unique = df["paper_id"].is_unique
    print(f"1. Unique paper_id check: {'PASS' if is_unique else 'FAIL'}")
    if not is_unique:
        duplicates = df[df.duplicated(subset=["paper_id"], keep=False)]["paper_id"].tolist()
        print(f"   Duplicate paper_ids: {duplicates}")
        
    # Check non-null/non-empty paper_id, title, summary, text_for_embedding, age_days
    null_counts = df[["paper_id", "title", "summary", "text_for_embedding", "age_days"]].isnull().sum()
    empty_strings = (df[["paper_id", "title", "summary", "text_for_embedding"]] == "").sum()
    
    print(f"2. Null value checks:")
    for col in null_counts.index:
        print(f"   - {col}: {null_counts[col]} nulls")
    print(f"3. Empty string checks:")
    for col in empty_strings.index:
        print(f"   - {col}: {empty_strings[col]} empty strings")
        
    # Check age_days >= 0
    negative_age = (df["age_days"] < 0).sum()
    print(f"4. Negative age_days check: {'PASS' if negative_age == 0 else 'FAIL'}")
    if negative_age > 0:
        print(f"   Number of records with negative age: {negative_age}")
        
    # Print sample record
    print("\n=== Cleaned Record Sample (First Row) ===")
    first_row = df.iloc[0].to_dict()
    for k, v in first_row.items():
        if k == "text_for_embedding":
            print(f"{k}: {str(v)[:150]}... [truncated]")
        elif k == "summary":
            print(f"{k}: {str(v)[:100]}... [truncated]")
        else:
            print(f"{k}: {v}")
            
    print("\nValidation completed successfully!")

if __name__ == "__main__":
    main()
