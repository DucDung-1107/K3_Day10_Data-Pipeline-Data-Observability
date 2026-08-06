"""Role 3: RAG & agent (MiniLM, Chroma, search, lookup).

Milestone tasks:
1. Create a separate papers-corrupted index from the corrupted clean data.
2. Re-run baseline queries to observe how retrieval changes between
   papers-baseline and papers-corrupted.
3. Verify papers-baseline is still readable and has NOT been mutated.
4. Create a separate papers-repaired index from the repaired clean data
   and re-run the same baseline queries.
5. Test the agent uses tools (semantic_search_papers, lookup_paper) and
   retrieval returns repaired documents.
6. Present the three separate collections/paths (baseline, corrupted, repaired).
"""
from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd

from core.config import load_settings
from core.utils import read_json, write_json
from retrieval.index import LocalEmbeddingIndex

# Directory where comparison artifacts for this role are written.
ROLE3_OUTPUT = Path(__file__).resolve().parents[1] / "data" / "results"


def save_payload(name: str, payload: object) -> Path:
    path = ROLE3_OUTPUT / name
    write_json(path, payload)
    print(f"  wrote {path.relative_to(Path(__file__).resolve().parents[1])}")
    return path


def load_dataframe(path: Path) -> pd.DataFrame:
    records = read_json(path)
    return pd.DataFrame(records)


def run_queries(index: LocalEmbeddingIndex, queries: list[str]) -> list[dict]:
    """Run semantic search over one index."""
    results = []
    for query in queries:
        search_hits = index.search(query, top_k=4)
        results.append(
            {
                "query": query,
                "search_hits": [
                    {
                        "paper_id": hit.paper_id,
                        "title": hit.title,
                        "score": round(float(hit.score), 4),
                    }
                    for hit in search_hits
                ],
            }
        )
    return results


def main() -> None:
    settings = load_settings()
    ROLE3_OUTPUT.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # TASK 1: Build a separate papers-corrupted collection from the
    # corrupted clean data so its manifest points at the LOCAL chroma dir.
    # ------------------------------------------------------------------
    print("=== TASK 1: Build papers-corrupted from corrupted clean data ===")
    df_corrupted = load_dataframe(settings.paths.corrupted_clean_json)
    print(f"Loaded {len(df_corrupted)} corrupted clean records from {settings.paths.corrupted_clean_json}")

    index_corrupted = LocalEmbeddingIndex.build(
        df_corrupted,
        settings,
        settings.paths.corrupted_embeddings_json,
    )
    print(f"Built index: collection={index_corrupted.collection_name} docs={len(index_corrupted.documents)}")

    # Verify the manifest now points at the local chroma dir.
    manifest = read_json(settings.paths.corrupted_embeddings_json)
    print(f"Manifest collection_name: {manifest['collection_name']}")
    print(f"Manifest persist_path: {manifest['persist_path']}")
    assert manifest["persist_path"] == str(settings.paths.chroma_dir), "persist_path was not fixed!"
    print("PASS: papers-corrupted manifest now references the local Chroma directory.")

    # Reload the corrupted index from the manifest to prove it is loadable.
    index_corrupted_reloaded = LocalEmbeddingIndex.load(settings, settings.paths.corrupted_embeddings_json)
    print(
        f"Reloaded corrupted index OK: collection={index_corrupted_reloaded.collection_name} "
        f"docs={len(index_corrupted_reloaded.documents)}"
    )

    # ------------------------------------------------------------------
    # TASK 3 (first): Snapshot baseline collection names/docs BEFORE any
    # mutation, then verify nothing changed after we built corrupted.
    # ------------------------------------------------------------------
    print("\n=== TASK 3: Verify papers-baseline is readable and NOT mutated ===")
    baseline_manifest = read_json(settings.paths.embeddings_json)
    baseline_paper_ids_before = {doc["paper_id"] for doc in baseline_manifest["documents"]}
    baseline_titles_before = {doc["title"] for doc in baseline_manifest["documents"]}
    print(f"Baseline manifest docs before: {len(baseline_paper_ids_before)}")

    # Load baseline index from the local manifest.
    index_baseline = LocalEmbeddingIndex.load(settings)
    print(f"Baseline loaded OK: collection={index_baseline.collection_name} docs={len(index_baseline.documents)}")

    # Verify readable via a quick search + lookup.
    probe_hits = index_baseline.search("retrieval augmented generation large language model", top_k=3)
    print(f"Baseline search probe returned {len(probe_hits)} hits: {[h.paper_id for h in probe_hits]}")

    lookup_probe = index_baseline.lookup("10-2118-234689-pa")
    print(f"Baseline lookup probe paper_id=10-2118-234689-pa -> found={lookup_probe is not None}")

    # Verify not mutated: compare manifest documents with what the collection returns.
    baseline_manifest_now = read_json(settings.paths.embeddings_json)
    baseline_paper_ids_after = {doc["paper_id"] for doc in baseline_manifest_now["documents"]}
    baseline_titles_after = {doc["title"] for doc in baseline_manifest_now["documents"]}

    collection_paper_ids = {doc["paper_id"] for doc in index_baseline.documents}
    manifest_paper_ids = baseline_paper_ids_after

    assert baseline_paper_ids_before == baseline_paper_ids_after, "Baseline manifest mutated!"
    assert baseline_titles_before == baseline_titles_after, "Baseline titles mutated!"
    assert collection_paper_ids == manifest_paper_ids, "Baseline collection docs differ from manifest!"
    assert len(index_baseline.documents) == 24, f"Expected 24 baseline docs, got {len(index_baseline.documents)}"

    print("PASS: papers-baseline is readable (search + lookup work) and NOT mutated (24 docs, same IDs & titles).")

    # ------------------------------------------------------------------
    # TASK 2: Re-run the baseline queries against both indexes to observe
    # how retrieval changes between papers-baseline and papers-corrupted.
    # ------------------------------------------------------------------
    print("\n=== TASK 2: Re-run baseline queries on both indexes ===")
    queries = [
        "What is the summary of the paper 'SafeRAG: A Large-Language-Model-Based Multistage Retrieval-Augmented Framework for Oil and Gas Safety Report Generation'?",
        "Who authored the paper 'SafeRAG: A Large-Language-Model-Based Multistage Retrieval-Augmented Framework for Oil and Gas Safety Report Generation'?",
        "retrieval augmented generation for large language models",
        "agentic AI framework for document retrieval",
        "hallucination mitigation in retrieval augmented generation",
        "The Age of Autonomous Agents: A Bibliometric Review of Agentic AI Architectures, Applications, and Emerging Challenges",
        "Chatbot Hybrid Fatwa MUI Menggunakan Retrieval Augmented Generation dan Large Language Model",
    ]

    baseline_results = run_queries(index_baseline, queries)
    corrupted_results = run_queries(index_corrupted_reloaded, queries)

    comparison = []
    for base_item, corr_item in zip(baseline_results, corrupted_results, strict=False):
        base_ids = [h["paper_id"] for h in base_item["search_hits"]]
        corr_ids = [h["paper_id"] for h in corr_item["search_hits"]]
        comparison.append(
            {
                "query": base_item["query"],
                "baseline_top4": base_item["search_hits"],
                "corrupted_top4": corr_item["search_hits"],
                "baseline_ids": base_ids,
                "corrupted_ids": corr_ids,
                "overlap": sorted(set(base_ids) & set(corr_ids)),
                "changed": base_ids != corr_ids,
            }
        )

    n_changed = sum(1 for item in comparison if item["changed"])
    print(f"\nBaseline vs Corrupted — ranking changed in {n_changed}/{len(comparison)} queries:")
    for item in comparison:
        status = "CHANGED" if item["changed"] else "same"
        print(f"\n  [{status}] {item['query'][:70]}...")
        print(f"    baseline : {item['baseline_ids']}")
        print(f"    corrupted: {item['corrupted_ids']}")

    # ------------------------------------------------------------------
    # TASK 4: Build a separate papers-repaired collection from the
    # repaired clean data so its manifest points at the LOCAL chroma dir.
    # ------------------------------------------------------------------
    print("\n=== TASK 4: Build papers-repaired from repaired clean data ===")
    df_repaired = load_dataframe(settings.paths.repaired_clean_json)
    print(f"Loaded {len(df_repaired)} repaired clean records from {settings.paths.repaired_clean_json}")

    index_repaired = LocalEmbeddingIndex.build(
        df_repaired,
        settings,
        settings.paths.repaired_embeddings_json,
    )
    print(f"Built index: collection={index_repaired.collection_name} docs={len(index_repaired.documents)}")

    # Verify the manifest now points at the local chroma dir.
    repaired_manifest = read_json(settings.paths.repaired_embeddings_json)
    print(f"Manifest collection_name: {repaired_manifest['collection_name']}")
    print(f"Manifest persist_path: {repaired_manifest['persist_path']}")
    assert repaired_manifest["persist_path"] == str(settings.paths.chroma_dir), "persist_path was not fixed!"
    print("PASS: papers-repaired manifest now references the local Chroma directory.")

    # Reload the repaired index from the manifest to prove it is loadable.
    index_repaired_reloaded = LocalEmbeddingIndex.load(settings, settings.paths.repaired_embeddings_json)
    print(
        f"Reloaded repaired index OK: collection={index_repaired_reloaded.collection_name} "
        f"docs={len(index_repaired_reloaded.documents)}"
    )

    # Re-run the same baseline queries on the repaired index.
    repaired_results = run_queries(index_repaired_reloaded, queries)

    # Compare baseline vs repaired.
    repaired_comparison = []
    for base_item, rep_item in zip(baseline_results, repaired_results, strict=False):
        base_ids = [h["paper_id"] for h in base_item["search_hits"]]
        rep_ids = [h["paper_id"] for h in rep_item["search_hits"]]
        repaired_comparison.append(
            {
                "query": base_item["query"],
                "baseline_top4": base_item["search_hits"],
                "repaired_top4": rep_item["search_hits"],
                "baseline_ids": base_ids,
                "repaired_ids": rep_ids,
                "overlap": sorted(set(base_ids) & set(rep_ids)),
                "changed": base_ids != rep_ids,
            }
        )

    n_repaired_changed = sum(1 for item in repaired_comparison if item["changed"])
    print(f"\nBaseline vs Repaired — ranking changed in {n_repaired_changed}/{len(repaired_comparison)} queries:")
    for item in repaired_comparison:
        status = "CHANGED" if item["changed"] else "same"
        print(f"\n  [{status}] {item['query'][:70]}...")
        print(f"    baseline: {item['baseline_ids']}")
        print(f"    repaired: {item['repaired_ids']}")

    # ------------------------------------------------------------------
    # TASK 5: Test the agent uses tools and retrieval returns repaired docs.
    # ------------------------------------------------------------------
    print("\n=== TASK 5: Test agent tool usage on repaired index ===")
    # Fall back to OpenAI if no Google key is configured.
    agent_settings = settings
    if not settings.google_api_key and settings.openai_api_key:
        agent_settings = dataclasses.replace(
            settings,
            llm_provider="openai",
            model_name="gpt-4o-mini",
        )
        print(f"Using OpenAI fallback: provider={agent_settings.llm_provider} model={agent_settings.model_name}")

    from retrieval.agent import build_agent, run_agent_question

    agent = build_agent(agent_settings, index_repaired_reloaded)
    print("Agent built on papers-repaired index.")

    agent_questions = [
        "Use the lookup tool to find the paper with paper_id '10-2118-234689-pa' and tell me its title.",
        "Use the semantic search tool to find papers about 'retrieval augmented generation for large language models' and list the top paper_id.",
    ]

    agent_results = []
    for question in agent_questions:
        print(f"\n  Q: {question}")
        try:
            answer = run_agent_question(agent, question)
            print(f"  A: {answer[:300]}")
            agent_results.append({"question": question, "answer": answer})
        except Exception as exc:
            print(f"  Agent FAILED: {exc}")
            agent_results.append({"question": question, "error": str(exc)})

    # ------------------------------------------------------------------
    # TASK 6: Present the three separate collections/paths.
    # ------------------------------------------------------------------
    print("\n=== TASK 6: Three separate collections/paths ===")
    collections_info = {
        "baseline": {
            "collection": "papers-baseline",
            "clean_data": str(settings.paths.clean_json),
            "embeddings_manifest": str(settings.paths.embeddings_json),
            "docs": len(index_baseline.documents),
            "persist_path": str(settings.paths.chroma_dir),
        },
        "corrupted": {
            "collection": "papers-corrupted",
            "clean_data": str(settings.paths.corrupted_clean_json),
            "embeddings_manifest": str(settings.paths.corrupted_embeddings_json),
            "docs": len(index_corrupted_reloaded.documents),
            "persist_path": str(settings.paths.chroma_dir),
        },
        "repaired": {
            "collection": "papers-repaired",
            "clean_data": str(settings.paths.repaired_clean_json),
            "embeddings_manifest": str(settings.paths.repaired_embeddings_json),
            "docs": len(index_repaired_reloaded.documents),
            "persist_path": str(settings.paths.chroma_dir),
        },
    }
    for name, info in collections_info.items():
        print(f"  {name}: collection={info['collection']} docs={info['docs']} manifest={info['embeddings_manifest']}")

    # Save all artifacts.
    payload = {
        "task": "role3_retrieval_comparison",
        "embeddings_model": settings.embedding_model,
        "collections": collections_info,
        "baseline_vs_corrupted": {
            "n_queries": len(comparison),
            "n_changed": n_changed,
            "comparison": comparison,
        },
        "baseline_vs_repaired": {
            "n_queries": len(repaired_comparison),
            "n_changed": n_repaired_changed,
            "comparison": repaired_comparison,
        },
        "agent_tool_test": agent_results,
    }
    save_payload("role3_retrieval_comparison.json", payload)

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    print("\n=== ROLE 3 SUMMARY ===")
    print(f"1. papers-corrupted rebuilt locally: {index_corrupted.collection_name} ({len(index_corrupted.documents)} docs)")
    print(f"2. Retrieval comparison (baseline vs corrupted): {n_changed}/{len(comparison)} queries changed")
    print(f"3. papers-baseline verified readable + NOT mutated: {len(index_baseline.documents)} docs")
    print(f"4. papers-repaired rebuilt locally: {index_repaired.collection_name} ({len(index_repaired.documents)} docs)")
    print(f"5. Retrieval comparison (baseline vs repaired): {n_repaired_changed}/{len(repaired_comparison)} queries changed")
    print(f"6. Agent tool test: {len(agent_results)} questions run on papers-repaired")
    print(f"7. Three collections: papers-baseline, papers-corrupted, papers-repaired — all in {settings.paths.chroma_dir}")


if __name__ == "__main__":
    main()