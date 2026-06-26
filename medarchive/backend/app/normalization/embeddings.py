"""Embedding provider with graceful degradation.

In the Docker profile sentence-transformers is installed and the MiniLM model is
baked into the image → real multilingual embeddings. On the host dev profile the
package may be absent → `available` is False and the matcher falls back to
lexical-only scoring. Nothing else in the codebase imports sentence-transformers.
"""
from __future__ import annotations

import logging
from functools import lru_cache

from app.config import settings

log = logging.getLogger("medarchive.embeddings")


class EmbeddingProvider:
    def __init__(self) -> None:
        self._model = None
        self._available = False
        if not settings.enable_embeddings:
            log.info("Embeddings disabled by config (lexical-only matching).")
            return
        try:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(settings.embedding_model)
            self._available = True
            log.info("Embedding model loaded: %s", settings.embedding_model)
        except Exception as exc:  # noqa: BLE001 - degrade gracefully
            log.warning("Embeddings unavailable (%s); falling back to lexical-only.", exc)

    @property
    def available(self) -> bool:
        return self._available

    def encode(self, text: str) -> list[float] | None:
        if not self._available:
            return None
        vec = self._model.encode([text], normalize_embeddings=True)[0]
        return [float(x) for x in vec]

    def encode_batch(self, texts: list[str]) -> list[list[float]] | None:
        if not self._available:
            return None
        vecs = self._model.encode(list(texts), normalize_embeddings=True)
        return [[float(x) for x in v] for v in vecs]


@lru_cache
def get_embedding_provider() -> EmbeddingProvider:
    return EmbeddingProvider()
