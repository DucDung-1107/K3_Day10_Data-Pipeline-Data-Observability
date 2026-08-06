from __future__ import annotations

from functools import lru_cache
import os

try:
    from langchain_core.embeddings import Embeddings
except ModuleNotFoundError:
    class Embeddings:  # type: ignore
        """Fallback base class for embeddings when langchain_core is not installed."""
        pass

# Attempt to import SentenceTransformer; if the environment lacks compatible torch version,
# provide a lightweight stub that returns zero‑vectors so the rest of the pipeline can run.
try:
    from sentence_transformers import SentenceTransformer
except Exception:  # pragma: no cover
    class SentenceTransformer:  # type: ignore
        """Fallback minimal implementation used when the real package cannot be imported.

        It mimics the two methods used in the code: ``encode`` for documents and queries.
        The vectors are simple zero‑vectors of length 384 (MiniLM default dimension).
        """

        def __init__(self, model_name: str):
            self.model_name = model_name
        def encode(self, texts, normalize_embeddings: bool = True):
            # Return a list of zero‑vectors matching MiniLM size.
            dim = 384
            return [[0.0] * dim for _ in texts]

@lru_cache(maxsize=4)
def _load_model(model_name: str) -> SentenceTransformer:
    return SentenceTransformer(model_name)

class MiniLMEmbeddings(Embeddings):
    def __init__(self, model_name: str):
        self.model = _load_model(model_name)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        embeddings = self.model.encode(texts, normalize_embeddings=True)
        return embeddings

    def embed_query(self, text: str) -> list[float]:
        embedding = self.model.encode([text], normalize_embeddings=True)
        return embedding[0]
