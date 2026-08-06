import sys
import json
from pathlib import Path
import pandas as pd
from datetime import datetime, UTC
import dataclasses

# Add src to python path
sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from core.config import load_settings
from retrieval.index import LocalEmbeddingIndex
from evaluation.testset import build_test_set
from retrieval.agent import build_agent, run_agent_question
from core.utils import read_json, safe_slug

def main():
    # 1. Load settings
    settings = load_settings()
    
    # 2. Check if clean JSON exists
    clean_json_path = settings.paths.clean_json
    if not clean_json_path.exists():
        print(f"Error: Clean dataset not found at {clean_json_path}. Please run validate_clean_data.py first.")
        sys.exit(1)
        
    print(f"Loading cleaned data from {clean_json_path}...")
    df = pd.read_json(clean_json_path)
    
    # 3. Verify no empty text_for_embedding and no duplicate paper_ids (CP2 task 4)
    print("\n--- CP2 Task 4: Verifying clean data constraints ---")
    assert not df["text_for_embedding"].isnull().any(), "Found null text_for_embedding!"
    assert (df["text_for_embedding"].str.strip() != "").all(), "Found empty text_for_embedding!"
    assert df["paper_id"].is_unique, "Found duplicate paper_ids!"
    print("Verification success: No empty text_for_embedding and all paper_ids are unique.")
    
    # 4. Build Chroma index
    print("\nBuilding Chroma baseline index...")
    index = LocalEmbeddingIndex.build(df, settings, settings.paths.embeddings_json)
    print(f"Chroma index built with collection: {index.collection_name}")
    
    # 5. Build evaluation test set (CP2 task 5)
    print("\n--- CP2 Task 5: Building test set & reviewing rows ---")
    test_set = build_test_set(df, settings.paths.eval_testset)
    print("Test set rows review:")
    for item in test_set[:4]: # print first 4 questions (representing the first paper)
        print(f"  - [{item['question_type'].upper()}] Q: {item['question']}")
        print(f"    Ground Truth: {item['ground_truth']}")
        print(f"    Doc ID: {item['ground_truth_doc_ids']}")
        
    # 6. Verify paper_id lineage from Raw -> Clean -> Index (CP2 task 1)
    print("\n--- CP2 Task 1: Lineage Verification ---")
    test_paper = df.iloc[0]
    target_paper_id = test_paper["paper_id"]
    print(f"Targeting paper_id: {target_paper_id}")
    
    # Step A: Find in raw response
    raw_response_path = settings.paths.raw_api_response
    raw_response = read_json(raw_response_path)
    raw_items = raw_response.get("message", {}).get("items", [])
    found_in_raw_response = False
    for item in raw_items:
        doi = item.get("DOI", "")
        if safe_slug(doi) == target_paper_id:
            found_in_raw_response = True
            print(f"  [1/4] Raw Response: Found matching DOI '{doi}' in {raw_response_path.name}")
            break
            
    # Step B: Find in raw records
    raw_records_path = settings.paths.raw_records_json
    raw_records = read_json(raw_records_path)
    found_in_raw_records = any(r["paper_id"] == target_paper_id for r in raw_records)
    print(f"  [2/4] Raw Records: {'Found' if found_in_raw_records else 'NOT found'} in {raw_records_path.name}")
    
    # Step C: Find in clean JSON
    print(f"  [3/4] Clean Dataset: Found record with title '{test_paper['title']}'")
    
    # Step D: Find in Index
    index_record = index.lookup(target_paper_id)
    if index_record:
        print(f"  [4/4] Chroma Index: Lookup succeeded!")
        print(f"        Indexed Title: {index_record['title']}")
        print(f"        Indexed Metadata Published: {index_record['metadata']['published']}")
    else:
        print(f"  [4/4] Chroma Index: Lookup FAILED!")
        
    # 7. Semantic Search smoke test
    search_query = "oil and gas safety report"
    print(f"\nRunning semantic search smoke test for query: '{search_query}'...")
    search_results = index.search(search_query, top_k=2)
    for i, res in enumerate(search_results):
        print(f"  Result {i+1}: paper_id: {res.paper_id}, score: {res.score:.4f}, title: {res.title}")
        
    # 8. Agent smoke test
    print("\n--- Running Agent Smoke Test ---")
    override_settings = settings
    if not settings.google_api_key and settings.openai_api_key:
        print("GOOGLE_API_KEY is empty. Overriding provider to 'openai' for agent test.")
        override_settings = dataclasses.replace(
            settings,
            llm_provider="openai",
            model_name="gpt-4o-mini"
        )
        
    try:
        agent = build_agent(override_settings, index)
        test_question = f"Who authored the paper '{test_paper['title']}'?"
        print(f"Asking agent: '{test_question}'")
        answer = run_agent_question(agent, test_question)
        print(f"Agent Answer: {answer}")
    except Exception as e:
        print(f"Agent smoke test warning/error: {e}")
        print("Note: Agent execution requires valid API keys in the environment.")

if __name__ == "__main__":
    main()
