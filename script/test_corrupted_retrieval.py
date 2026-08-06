from __future__ import annotations

import sys
from pathlib import Path

# Add src to python path
sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd
from core.config import load_settings
from retrieval.index import LocalEmbeddingIndex

def main() -> None:
    settings = load_settings()
    
    # 1. Build papers-corrupted separately
    print("=== TASK 1: Building papers-corrupted index ===")
    corrupted_json_path = settings.paths.corrupted_clean_json
    if not corrupted_json_path.exists():
        print(f"Error: Corrupted JSON path {corrupted_json_path} does not exist. Run corruption flow first.")
        sys.exit(1)
        
    df_corrupted = pd.read_json(corrupted_json_path)
    print(f"Loaded {len(df_corrupted)} corrupted records.")
    
    # Build collection papers-corrupted
    index_corrupted = LocalEmbeddingIndex.build(
        df=df_corrupted,
        settings=settings,
        embeddings_output_path=settings.paths.corrupted_embeddings_json
    )
    print(f"Created separate index: '{index_corrupted.collection_name}' with {len(index_corrupted.documents)} documents.")
    
    # 2. Check papers-baseline is still readable and not mutated
    print("\n=== TASK 3: Verifying papers-baseline is readable and not mutated ===")
    index_baseline = LocalEmbeddingIndex.load(
        settings=settings,
        embeddings_path=settings.paths.embeddings_json
    )
    print(f"Loaded baseline index collection: '{index_baseline.collection_name}' with {len(index_baseline.documents)} documents.")
    
    # Verifying lookup of dropped DOI in baseline vs corrupted
    target_doi = "10-2118-234689-pa"
    record_baseline = index_baseline.lookup(target_doi)
    record_corrupted = index_corrupted.lookup(target_doi)
    
    print(f"Lookup DOI '{target_doi}' in baseline: {'FOUND (Unmutated)' if record_baseline else 'MISS'}")
    print(f"Lookup DOI '{target_doi}' in corrupted: {'FOUND' if record_corrupted else 'MISS (Expected, successfully dropped)'}")
    
    assert record_baseline is not None, "Error: baseline collection was mutated or deleted!"
    assert record_corrupted is None, "Error: corrupted collection still contains the dropped DOI!"
    print("Lineage/Integrity Verification: PASS!")

    # 3. Run queries on both indexes to observe changes
    print("\n=== TASK 2: Running queries to compare retrieval ===")
    test_queries = [
        "SafeRAG oil and gas safety report generation",
        "retrieval augmented generation large language models",
        "economic security of dairy industry enterprises",
    ]
    
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        
        # Search in baseline
        results_baseline = index_baseline.search(query, top_k=2)
        print("  [Baseline Index]")
        for r in results_baseline:
            print(f"    - [{r.score:.4f}] {r.paper_id} | {r.title[:60]}")
            
        # Search in corrupted
        results_corrupted = index_corrupted.search(query, top_k=2)
        print("  [Corrupted Index]")
        for r in results_corrupted:
            print(f"    - [{r.score:.4f}] {r.paper_id} | {r.title[:60]}")

if __name__ == "__main__":
    main()
