"""The normalization & matching engine (brief §8) — the crux of the product.

Standalone and unit-testable: the scoring core operates over an in-memory
`ServiceIndex` (built from the services table), so it can be tested with plain
dicts and runs identically on both profiles. Semantic scoring is in-memory
cosine over precomputed embeddings (fast enough for the demo directory); it is
simply skipped when embeddings are unavailable (lexical-only fallback).

Pipeline per raw name:
  preprocess → exact/synonym (1.0) → lexical (RapidFuzz) → semantic (cosine)
  → weighted fusion → specialty boost → thresholded decision.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from rapidfuzz import fuzz, process

from app.config import settings
from app.normalization.embeddings import EmbeddingProvider, get_embedding_provider
from app.normalization.preprocess import canonicalize

AUTO = "auto"
REVIEW = "review"
UNMATCHED = "unmatched"


@dataclass
class Candidate:
    service_id: str
    service_name: str
    category: str
    score: float
    method: str  # exact | synonym | lexical | semantic
    lexical: float = 0.0
    semantic: float = 0.0

    def as_dict(self) -> dict:
        return {
            "service_id": self.service_id,
            "service_name": self.service_name,
            "category": self.category,
            "score": round(self.score, 4),
            "method": self.method,
            "lexical": round(self.lexical, 4),
            "semantic": round(self.semantic, 4),
        }


@dataclass
class IndexedService:
    service_id: str
    service_name: str
    category: str
    canonical: str
    synonyms_canonical: list[str]
    embedding: list[float] | None = None


@dataclass
class ServiceIndex:
    """Searchable view of the directory. Build once, query many."""

    services: list[IndexedService] = field(default_factory=list)
    _canon_to_idx: dict[str, int] = field(default_factory=dict)
    _syn_to_idx: dict[str, int] = field(default_factory=dict)

    @classmethod
    def from_rows(cls, rows: list[dict]) -> "ServiceIndex":
        """rows: {service_id, service_name, category, synonyms?, embedding?}."""
        idx = cls()
        for r in rows:
            canon = canonicalize(r["service_name"])
            syns = [canonicalize(s) for s in (r.get("synonyms") or [])]
            svc = IndexedService(
                service_id=r["service_id"],
                service_name=r["service_name"],
                category=r["category"],
                canonical=canon,
                synonyms_canonical=syns,
                embedding=r.get("embedding"),
            )
            i = len(idx.services)
            idx.services.append(svc)
            idx._canon_to_idx.setdefault(canon, i)
            for s in syns:
                idx._syn_to_idx.setdefault(s, i)
        return idx

    def __len__(self) -> int:
        return len(self.services)

    def exact_or_synonym(self, canon: str) -> tuple[int, str] | None:
        if canon in self._canon_to_idx:
            return self._canon_to_idx[canon], "exact"
        if canon in self._syn_to_idx:
            return self._syn_to_idx[canon], "synonym"
        return None


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


class Matcher:
    def __init__(
        self,
        index: ServiceIndex,
        *,
        embedding_provider: EmbeddingProvider | None = None,
        w_lexical: float | None = None,
        w_semantic: float | None = None,
        auto_threshold: float | None = None,
        review_threshold: float | None = None,
    ) -> None:
        self.index = index
        self.provider = embedding_provider or get_embedding_provider()
        self.w_lexical = settings.match_fusion_lexical if w_lexical is None else w_lexical
        self.w_semantic = settings.match_fusion_semantic if w_semantic is None else w_semantic
        self.auto_threshold = settings.match_threshold_auto if auto_threshold is None else auto_threshold
        self.review_threshold = settings.match_threshold_review if review_threshold is None else review_threshold

    # ── scoring stages ──────────────────────────────────────────────────────
    def _lexical_scores(self, canon: str, limit: int) -> dict[int, float]:
        names = [s.canonical for s in self.index.services]
        # WRatio handles partial / token reordering well for medical names.
        hits = process.extract(canon, names, scorer=fuzz.WRatio, limit=limit)
        return {idx: score / 100.0 for _, score, idx in hits}

    def _semantic_scores(self, canon: str, candidate_idxs: list[int]) -> dict[int, float]:
        if not self.provider.available:
            return {}
        q = self.provider.encode(canon)
        if q is None:
            return {}
        out: dict[int, float] = {}
        for i in candidate_idxs:
            emb = self.index.services[i].embedding
            if emb:
                out[i] = max(0.0, _cosine(q, emb))
        return out

    # ── public API ──────────────────────────────────────────────────────────
    def match(
        self, raw_name: str, *, specialty_hint: str | None = None, top_k: int = 5
    ) -> list[Candidate]:
        canon = canonicalize(raw_name)
        if not canon:
            return []

        # 1. exact / synonym short-circuit.
        hit = self.index.exact_or_synonym(canon)
        if hit is not None:
            i, method = hit
            svc = self.index.services[i]
            return [
                Candidate(
                    service_id=svc.service_id,
                    service_name=svc.service_name,
                    category=svc.category,
                    score=1.0,
                    method=method,
                    lexical=1.0,
                    semantic=1.0 if self.provider.available else 0.0,
                )
            ]

        # 2. lexical candidate pool (wider than top_k so semantic can re-rank).
        pool = max(top_k * 4, 20)
        lexical = self._lexical_scores(canon, pool)
        if not lexical:
            return []
        semantic = self._semantic_scores(canon, list(lexical.keys()))

        # 3. fuse.
        use_semantic = bool(semantic)
        candidates: list[Candidate] = []
        for i, lex in lexical.items():
            sem = semantic.get(i, 0.0)
            if use_semantic:
                fused = self.w_lexical * lex + self.w_semantic * sem
                method = "semantic" if sem >= lex else "lexical"
            else:
                fused = lex  # lexical-only profile
                method = "lexical"
            svc = self.index.services[i]
            # 4. specialty disambiguation boost.
            if specialty_hint and specialty_hint.strip():
                if canonicalize(specialty_hint) in canonicalize(svc.category):
                    fused = min(1.0, fused + 0.05)
            candidates.append(
                Candidate(
                    service_id=svc.service_id,
                    service_name=svc.service_name,
                    category=svc.category,
                    score=fused,
                    method=method,
                    lexical=lex,
                    semantic=sem,
                )
            )

        candidates.sort(key=lambda c: c.score, reverse=True)
        return candidates[:top_k]

    def classify(self, score: float) -> str:
        if score >= self.auto_threshold:
            return AUTO
        if score >= self.review_threshold:
            return REVIEW
        return UNMATCHED
