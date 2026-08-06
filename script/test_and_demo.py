"""
Verification & Demo Script for Phase-1

Runs the following checks and demonstrations:
1. Verify that the cleaned CSV/JSON and the embeddings manifest have the same number of records.
2. Load the Chroma index and perform a semantic search example.
3. Perform an exact lookup by paper_id.
4. Run the full evaluation pipeline, including RAGAS if enabled.

All outputs are printed to stdout.
"""

import json

import pandas as pd

import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


from src.core.config import load_settings
try:
    from src.evaluation.metrics import evaluate_pipeline
except ModuleNotFoundError:
    evaluate_pipeline = None  # Evaluation will be skipped if dependencies are missing
from src.retrieval.index import LocalEmbeddingIndex


def verify_counts(settings):
    """Verify that cleaned records and embedding documents have matching counts."""
    df = pd.read_csv(settings.paths.clean_csv)
    clean_count = len(df)

    with open(settings.paths.embeddings_json, "r", encoding="utf-8") as file:
        manifest = json.load(file)

    embed_count = len(manifest.get("documents", []))

    print(f"🔎 Cleaned records: {clean_count}")
    print(f"📐 Embedding documents: {embed_count}")

    if clean_count != embed_count:
        print("⚠️ Mismatch! The dataset and embedding manifest are out of sync.")
    else:
        print("✅ Counts match.")

    return df


def demo_semantic_search(settings, df):
    """Load the persisted index and run a semantic search example."""
    del df  # Kept in the signature for compatibility with the original script.

    index = LocalEmbeddingIndex.load(settings)
    query = "graph neural networks for drug discovery"

    print(f"\n🔎 Semantic search for: '{query}'")
    results = index.search(query, top_k=3)

    for position, result in enumerate(results, start=1):
        print(
            f"{position}. [{result.paper_id}] "
            f"{result.title[:120]} "
            f"(score={result.score:.3f})"
        )


def demo_exact_lookup(settings):
    """Look up the first paper_id from the embeddings manifest."""
    index = LocalEmbeddingIndex.load(settings)

    with open(settings.paths.embeddings_json, "r", encoding="utf-8") as file:
        manifest = json.load(file)

    documents = manifest.get("documents", [])
    if not documents:
        print("\n⚠️ The embeddings manifest contains no documents.")
        return

    first_doc = documents[0]
    paper_id = first_doc["paper_id"].lower()

    print(f"\n🔎 Exact lookup for paper_id: {paper_id}")
    doc = index.lookup(paper_id)

    if doc:
        title = doc.get("title", "")
        summary = doc.get("metadata", {}).get("summary", "")
        print(f"Title: {title}\nSummary: {summary[:200]}…")
    else:
        print("⚠️ Not found.")


def run_evaluation(settings, df):
    """Build or reuse the index and run the evaluation pipeline if available."""
    index = LocalEmbeddingIndex.build(df, settings)
    if evaluate_pipeline is None:
        print("\n⚠️ Evaluation skipped: 'datasets' package not installed.")
        return
    bundle = evaluate_pipeline(
        settings,
        index,
        settings.paths.eval_testset,
        settings.paths.baseline_metrics,
        settings.paths.baseline_answers,
    )
    print("\n📊 Evaluation summary:")
    for key, value in bundle.summary.items():
        print(f"{key}: {value}")


def main():
    """Run all Phase-1 verification and demonstration steps."""
    settings = load_settings()

    df = verify_counts(settings)
    demo_semantic_search(settings, df)
    demo_exact_lookup(settings)
    run_evaluation(settings, df)


if __name__ == "__main__":
    main()