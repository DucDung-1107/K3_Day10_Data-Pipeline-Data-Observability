import sys
import dataclasses
from pathlib import Path
import pandas as pd

# Add src to python path
sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from core.config import load_settings
from retrieval.index import LocalEmbeddingIndex
from retrieval.agent import build_agent

def main():
    print("=== STEP 1: LOAD SETTINGS & CREATE EMBEDDINGS + CHROMA COLLECTION ===")
    settings = load_settings()
    
    # Auto fallback to OpenAI if no Google API Key
    if not settings.google_api_key:
        print("GOOGLE_API_KEY not found. Fallback to OpenAI for testing...")
        settings = dataclasses.replace(
            settings,
            llm_provider="openai",
            model_name="gpt-4o-mini"
        )
        
    print(f"LLM Provider: {settings.llm_provider}")
    print(f"LLM Model: {settings.model_name}")
    print(f"Embedding Model: {settings.embedding_model}")
    print(f"Collection Name: {settings.baseline_collection_name}")
    
    clean_json_path = settings.paths.clean_json
    print(f"Read clean data from: {clean_json_path}")
    df = pd.read_json(clean_json_path)
    print(f"Loaded {len(df)} clean documents.")
    
    print("Building LocalEmbeddingIndex (Generating embeddings and Chroma collection)...")
    index = LocalEmbeddingIndex.build(df, settings)
    print("Index built successfully!")
    
    print("\n=== STEP 2: TEST DIRECT RETRIEVAL (DIRECT RETRIEVAL TEST) ===")
    # 1. Semantic Search Test
    query_semantic = "What is Deep RAG and multi-step reasoning?"
    print(f"\n[Test 1] Semantic Search with query: '{query_semantic}'")
    search_results = index.search(query_semantic, top_k=2)
    for i, res in enumerate(search_results):
        print(f"  Top {i+1} Match:")
        print(f"    Paper ID: {res.paper_id}")
        print(f"    Title: {res.title}")
        print(f"    Score (Similarity): {res.score:.4f}")
        print(f"    Metadata (eff_date): {res.metadata.get('eff_date')}")
        print(f"    Metadata (owner): {res.metadata.get('owner')}")
        print(f"    Metadata (src_url): {res.metadata.get('src_url')}")
        
    # 2. Exact Lookup Test
    paper_id_lookup = "10-21203-rs-3-rs-10012178-v1"
    print(f"\n[Test 2] Exact Lookup with paper_id: '{paper_id_lookup}'")
    lookup_result = index.lookup(paper_id_lookup)
    if lookup_result:
        print("  Found exact paper:")
        print(f"    Title: {lookup_result['title']}")
        print(f"    Published: {lookup_result['published']}")
        print(f"    Authors: {lookup_result['authors_joined']}")
    else:
        print("  Paper not found!")
        
    print("\n=== STEP 3: TEST AGENT & VALIDATE TOOL CALLS (AGENT TOOL-USE TEST) ===")
    print("Building Agent...")
    agent = build_agent(settings, index)
    print("Agent built successfully.")
    
    question = (
        "Which paper is titled 'SafeRAG: A Large-Language-Model-Based Multistage Retrieval-Augmented "
        "Framework for Oil and Gas Safety Report Generation'? Please use the lookup tool to find the exact details."
    )
    print(f"\nSend question to Agent: '{question}'\n")
    
    # Invoke agent
    result = agent.invoke({"messages": [{"role": "user", "content": question}]})
    
    # Print dialogue history
    messages = result.get("messages", [])
    print("--- MESSAGE DIALOG HISTORY ---")
    for i, msg in enumerate(messages):
        role = getattr(msg, "role", "unknown")
        msg_type = msg.__class__.__name__
        print(f"\nMessage #{i+1} [{msg_type}]:")
        
        # Print tool_calls if any
        tool_calls = getattr(msg, "tool_calls", [])
        if tool_calls:
            print(f"  [Tool Calls]: {tool_calls}")
            
        content = getattr(msg, "content", "")
        if content:
            snippet = content if len(content) < 300 else content[:300] + "..."
            print(f"  [Content]: {snippet}")
            
    print("\n=== AGENT VALIDATION COMPLETED SUCCESSFULLY ===")

if __name__ == "__main__":
    main()
