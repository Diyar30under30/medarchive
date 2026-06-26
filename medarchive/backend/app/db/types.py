"""Portable column types so the SAME models run on SQLite (host dev) and
PostgreSQL+pgvector (Docker).

`EmbeddingType` stores a list[float]:
  - PostgreSQL → native pgvector `vector(dim)` column (real ANN/cosine in-DB).
  - SQLite     → JSON text; cosine is computed in Python (fine for the demo set).
"""
from __future__ import annotations

import json

from sqlalchemy import Text
from sqlalchemy.types import TypeDecorator

# paraphrase-multilingual-MiniLM-L12-v2 output dimension.
EMBEDDING_DIM = 384


class EmbeddingType(TypeDecorator):
    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            from pgvector.sqlalchemy import Vector

            return dialect.type_descriptor(Vector(EMBEDDING_DIM))
        return dialect.type_descriptor(Text())

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return list(value)  # pgvector handles the list directly
        return json.dumps(list(value))

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return list(value)
        return json.loads(value)
