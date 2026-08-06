"""Smoke test for retrieval: build index, run search + lookup, validate metadata.

Usage:
    uv run python script/smoke_retrieval.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# Add src to python path
sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd

from core.config import load_settings
from core.utils import read_json
from retrieval.index import LocalEmbeddingIndex

# Required minimal metadata fields per the finalized schema
REQUIRED_METADATA = {"eff_date", "owner", "src_url"}

# Smoke queries that should match the corpus (RAG / LLM / agentic topics)
SMOKE_QUERIES = [
    "retrieval augmented generation for large language models",
    "agentic AI framework for document retrieval",
    "medical large language model clinical decision support",
    "hallucination mitigation in retrieval augmented generation",
]

# Smoke lookups: (value, expected_field, expected_value)
SMOKE_LOOKUPS = [
    ("10-2118-234689-pa", "paper_id", "10-2118-234689-pa"),
    ("10-3390-app16052244", "paper_id", "10-3390-app16052244"),
    (
        "SafeRAG: A Large-Language-Model-Based Multistage Retrieval-Augmented Framework for Oil and Gas Safety Report Generation",
        "title",
        "SafeRAG: A Large-Language-Model-Based Multistage Retrieval-Augmented Framework for Oil and Gas Safety Report Generation",
    ),
]


def load_clean_dataframe(settings) -> pd.DataFrame:
    """Load the cleaned papers JSON into a DataFrame."""
    records = read_json(settings.paths.clean_json)
    return pd.DataFrame(records)


def validate_metadata(documents: list[dict]) -> list[str]:
    """Ensure every document carries the required minimal metadata fields."""
    missing: list[str] = []
    for doc in documents:
        meta = doc.get("metadata", {})
        for field in REQUIRED_METADATA:
            if field not in meta or meta[field] in (None, ""):
                missing.append(f"{doc.get('record_id', '?')} missing metadata field: {field}")
    return missing


def run_smoke_search(index: LocalEmbeddingIndex) -> None:
    print("\n=== SMOKE SEARCH ===")
    for query in SMOKE_QUERIES:
        results = index.search(query, top_k=3)
        print(f"\nQuery: {query!r}")
        if not results:
            print("  -> NO RESULTS")
            continue
        for r in results:
            print(f"  - [{r.score:.4f}] {r.paper_id} | {r.title[:80]}")
            print(f"      eff_date={r.metadata.get('eff_date')} owner={r.metadata.get('owner')} src_url={r.metadata.get('src_url')}")


def run_smoke_lookup(index: LocalEmbeddingIndex) -> None:
    print("\n=== SMOKE LOOKUP ===")
    for value, field, expected in SMOKE_LOOKUPS:
        record = index.lookup(value)
        if record is None:
            print(f"Lookup {value!r} -> MISS")
            continue
        actual = record.get(field)
        status = "PASS" if actual == expected else "FAIL"
        print(f"Lookup {value!r} -> {status} ({field}={actual!r})")


def main() -> None:
    settings = load_settings()
    print(f"Embedding model: {settings.embedding_model}")
    print(f"Baseline collection: {settings.baseline_collection_name}")
    print(f"Chroma persist path: {settings.paths.chroma_dir}")

    df = load_clean_dataframe(settings)
    print(f"Loaded {len(df)} cleaned records from {settings.paths.clean_json}")

    # Build the index (recreates the baseline collection)
    print("\nBuilding Chroma index...")
    index = LocalEmbeddingIndex.build(df, settings)
    print(f"Indexed {len(index.documents)} documents into collection '{index.collection_name}'")

    # Validate minimal metadata
    print("\n=== METADATA VALIDATION ===")
    missing = validate_metadata(index.documents)
    if missing:
        print(f"FAIL: {len(missing)} documents missing required metadata:")
        for line in missing[:10]:
            print(f"  - {line}")
    else:
        print(f"PASS: all {len(index.documents)} documents have eff_date, owner, src_url")

    # Run smoke searches and lookups
    run_smoke_search(index)
    run_smoke_lookup(index)

    print("\nSmoke retrieval completed.")


if __name__ == "__main__":
    main()