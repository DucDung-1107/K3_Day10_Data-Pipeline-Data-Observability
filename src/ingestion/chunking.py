# src/ingestion/chunking.py
"""Utilities for splitting cleaned papers into smaller chunks for embedding."""

from __future__ import annotations

from datetime import datetime
from typing import Iterable

import pandas as pd
from langchain_text_splitters import RecursiveCharacterTextSplitter
# ---------------------------------------------------------------------------


def _split_text(text: str, splitter: RecursiveCharacterTextSplitter) -> Iterable[str]:
    """Yield non‑empty chunks from a single piece of text."""
    for chunk in splitter.split_text(text):
        chunk = chunk.strip()
        if chunk:
            yield chunk


def split_into_chunks(df: pd.DataFrame) -> pd.DataFrame:
    """
    Split each paper's ``text_for_embedding`` into overlapping chunks.

    The input dataframe must contain at least the columns produced by
    ``build_clean_dataframe`` (e.g. ``paper_id``, ``title``, ``text_for_embedding``).

    Returns a new dataframe where each row represents a chunk and carries
    the original paper metadata plus:

    * ``chunk_id`` – integer index of the chunk within the paper
    * ``content`` – the actual chunk text (used for embedding)
    * ``start_pos`` / ``end_pos`` – character offsets within the original text
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,   # ~500 characters per chunk (tunable)
        chunk_overlap=50, # overlap to preserve context across chunks
        length_function=len,
    )

    chunk_rows = []

    for _, row in df.iterrows():
        paper_id = row["paper_id"]
        title = row["title"]
        base_text = row["text_for_embedding"]

        # Split and record offsets
        start = 0
        for chunk_id, chunk in enumerate(_split_text(base_text, splitter)):
            end = start + len(chunk)
            chunk_rows.append(
                {
                    "paper_id": paper_id,
                    "title": title,
                    "chunk_id": chunk_id,
                    "content": chunk,
                    "start_pos": start,
                    "end_pos": end,
                    # Preserve minimal metadata that the index expects
                    "eff_date": row.get("published"),
                    "owner": row.get("authors_joined", "").split(",")[0].strip(),
                    "src_url": row.get("abs_url"),
                    # Keep the original columns for possible downstream use
                    **{k: v for k, v in row.items() if k not in ("paper_id", "title", "text_for_embedding")},
                }
            )
            start = end - splitter.chunk_overlap  # overlap for next chunk

    return pd.DataFrame(chunk_rows)


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Simple sanity test – can be run directly
    sample = pd.DataFrame(
        {
            "paper_id": ["p1"],
            "title": ["Sample paper"],
            "text_for_embedding": [
                "Lorem ipsum dolor sit amet, consectetur adipiscing elit. " * 20
            ],
        }
    )
    chunks = split_into_chunks(sample)
    print(chunks[["paper_id", "chunk_id", "content"]].head())
