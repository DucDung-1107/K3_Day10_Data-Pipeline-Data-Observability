from __future__ import annotations

from pathlib import Path
from typing import Any
import pandas as pd

from core.utils import write_json, first_sentence


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Build evaluation test set from the cleaned dataframe.

    Generates 4 questions per paper (summary, authors, date, categories)
    aligned with retrieval/qa.py's answer extraction patterns.
    """
    if len(df) < 5:
        raise ValueError("Dataframe must have at least 5 records to generate a representative test set.")

    # Select the first 6 papers to generate 24 questions (avoids high LLM costs while remaining representative)
    selected_papers = df.head(6).to_dict(orient="records")
    test_set = []
    question_counter = 1

    for row in selected_papers:
        title = row["title"]
        paper_id = row["paper_id"]

        # 1. Summary question (does not trigger specific keywords -> falls back to first_sentence of summary)
        test_set.append({
            "id": f"Q{question_counter:03d}",
            "question_type": "summary",
            "question": f"What is the summary of the paper '{title}'?",
            "ground_truth": first_sentence(row["summary"]),
            "ground_truth_doc_ids": [paper_id]
        })
        question_counter += 1

        # 2. Authors question (triggers "who authored" keyword in qa.py -> retrieves authors_joined)
        test_set.append({
            "id": f"Q{question_counter:03d}",
            "question_type": "authors",
            "question": f"Who authored the paper '{title}'?",
            "ground_truth": row["authors_joined"],
            "ground_truth_doc_ids": [paper_id]
        })
        question_counter += 1

        # 3. Date question (triggers "when was" keyword in qa.py -> retrieves published date)
        test_set.append({
            "id": f"Q{question_counter:03d}",
            "question_type": "date",
            "question": f"When was the paper '{title}' published?",
            "ground_truth": row["published"],
            "ground_truth_doc_ids": [paper_id]
        })
        question_counter += 1

        # 4. Categories question (triggers "what categories" keyword in qa.py -> retrieves categories_joined)
        test_set.append({
            "id": f"Q{question_counter:03d}",
            "question_type": "categories",
            "question": f"What categories does the paper '{title}' belong to?",
            "ground_truth": row["categories_joined"],
            "ground_truth_doc_ids": [paper_id]
        })
        question_counter += 1

    write_json(Path(output_path), test_set)
    print(f"Generated {len(test_set)} test questions and saved to {output_path}")
    return test_set

