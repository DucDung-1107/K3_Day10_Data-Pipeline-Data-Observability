"""Check current state for Role 3: RAG & agent (MiniLM, Chroma, search, lookup)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from core.config import load_settings
from core.utils import read_json
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    settings = load_settings()
    print(f"Local chroma dir: {settings.paths.chroma_dir}")

    for name, path in [
        ("baseline", settings.paths.embeddings_json),
        ("corrupted", settings.paths.corrupted_embeddings_json),
        ("repaired", settings.paths.repaired_embeddings_json),
    ]:
        payload = read_json(path)
        print(
            f"{name}: collection={payload['collection_name']} "
            f"persist_path={payload['persist_path']} docs={len(payload['documents'])}"
        )

    # Try loading baseline index from local manifest
    print("\nAttempting load baseline index (local manifest)...")
    try:
        baseline = LocalEmbeddingIndex.load(settings)
        print(f"Baseline loaded OK: collection={baseline.collection_name} docs={len(baseline.documents)}")
    except Exception as exc:
        print(f"Baseline load FAILED: {exc}")

    # Try loading corrupted index - will fail if persist_path points to another machine
    print("\nAttempting load corrupted index (manifest)...")
    try:
        corrupted = LocalEmbeddingIndex.load(settings, settings.paths.corrupted_embeddings_json)
        print(f"Corrupted loaded OK: collection={corrupted.collection_name} docs={len(corrupted.documents)}")
    except Exception as exc:
        print(f"Corrupted load FAILED: {exc}")


if __name__ == "__main__":
    main()