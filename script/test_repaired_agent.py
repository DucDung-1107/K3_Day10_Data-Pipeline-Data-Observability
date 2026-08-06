from __future__ import annotations

import sys
import dataclasses
from pathlib import Path

# Add src to python path
sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd
from core.config import load_settings
from retrieval.index import LocalEmbeddingIndex
from retrieval.agent import build_agent

def main() -> None:
    settings = load_settings()
    
    # Auto fallback to OpenAI if no Google API Key
    if not settings.google_api_key:
        settings = dataclasses.replace(
            settings,
            llm_provider="openai",
            model_name="gpt-4o-mini"
        )

    # 1. Present the three separate collection configurations (Paths & Names)
    print("=== TASK 3: PRESENTING THREE SEPARATE COLLECTIONS ===")
    print(f"1. Baseline Collection: '{settings.baseline_collection_name}'")
    print(f"   Manifest Path: {settings.paths.embeddings_json}")
    
    print(f"2. Corrupted Collection: '{settings.corrupted_collection_name}'")
    print(f"   Manifest Path: {settings.paths.corrupted_embeddings_json}")
    
    print(f"3. Repaired Collection: '{settings.repaired_collection_name}'")
    print(f"   Manifest Path: {settings.paths.repaired_embeddings_json}")
    
    print(f"Chroma DB Directory: {settings.paths.chroma_dir}\n")

    # 2. Load papers-repaired index and query it directly
    print("=== TASK 1: LOADING REPAIRED INDEX & QUERYING DIRECTLY ===")
    index_repaired = LocalEmbeddingIndex.load(
        settings=settings,
        embeddings_path=settings.paths.repaired_embeddings_json
    )
    print(f"Loaded index '{index_repaired.collection_name}' with {len(index_repaired.documents)} documents.")
    
    # Baseline query check
    query = "SafeRAG oil and gas safety report"
    print(f"Querying repaired index directly for: '{query}'")
    results = index_repaired.search(query, top_k=1)
    for r in results:
        print(f"  Result found: [{r.score:.4f}] {r.paper_id} | {r.title}")
        assert r.paper_id == "10-2118-234689-pa", "Error: SafeRAG paper was not recovered in repaired index!"
    print("Direct retrieval verification on repaired index: PASS!\n")

    # 3. Test Agent Tool Use on Repaired Collection
    print("=== TASK 2: TESTING AGENT TOOL USE ON REPAIRED INDEX ===")
    print("Building Agent on top of index-repaired...")
    agent = build_agent(settings, index_repaired)
    
    question = "Who authored the paper 'SafeRAG: A Large-Language-Model-Based Multistage Retrieval-Augmented Framework for Oil and Gas Safety Report Generation'?"
    print(f"Asking Agent: '{question}'")
    
    # Invoke Agent
    response = agent.invoke({"messages": [{"role": "user", "content": question}]})
    messages = response.get("messages", [])
    
    print("\nDialogue Trace:")
    for i, msg in enumerate(messages):
        msg_type = msg.__class__.__name__
        print(f"\nMessage #{i+1} [{msg_type}]:")
        
        # Check for tool calls
        tool_calls = getattr(msg, "tool_calls", [])
        if tool_calls:
            print(f"  [Tool Calls]: {tool_calls}")
            
        content = getattr(msg, "content", "")
        if content:
            snippet = content if len(content) < 300 else content[:300] + "..."
            print(f"  [Content]: {snippet}")
            
    print("\nVerification Completed successfully!")

if __name__ == "__main__":
    main()
