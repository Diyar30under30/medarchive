"""Matching engine unit tests — pure logic, no DB / no embeddings (lexical-only)."""
from __future__ import annotations

import pytest

from app.normalization.preprocess import canonicalize, tokens
from app.normalization.matcher import Matcher, ServiceIndex


# A small in-memory directory mirroring the synthetic one's shape.
ROWS = [
    {"service_id": "s1", "service_name": "Общий анализ крови", "category": "Гематология", "synonyms": []},
    {"service_id": "s2", "service_name": "Общий анализ мочи", "category": "Общеклинические исследования", "synonyms": []},
    {"service_id": "s3", "service_name": "Тиреотропный гормон (ТТГ)", "category": "ИФА", "synonyms": []},
    {"service_id": "s4", "service_name": "Глюкоза", "category": "Биохимия", "synonyms": []},
    {"service_id": "s5", "service_name": "УЗИ органов брюшной полости", "category": "УЗИ", "synonyms": []},
    {"service_id": "s6", "service_name": "Консультация терапевта", "category": "Консультации специалистов", "synonyms": []},
    {"service_id": "s7", "service_name": "Удаление папиллом", "category": "Дерматология", "synonyms": []},
    {"service_id": "s8", "service_name": "Удаление папиллом", "category": "Хирургия", "synonyms": []},
]


@pytest.fixture
def matcher() -> Matcher:
    return Matcher(ServiceIndex.from_rows(ROWS))


# ── preprocess ──────────────────────────────────────────────────────────────
def test_canonicalize_lowercases_and_strips():
    assert canonicalize("  Креатинин  ") == "креатинин"


def test_canonicalize_expands_abbreviation():
    assert "общий анализ крови" in canonicalize("ОАК")


def test_canonicalize_drops_noise_qualifier():
    out = canonicalize("Консультация терапевта (взрослый)")
    assert "взрослый" not in out
    assert "консультация" in out and "терапевта" in out


def test_canonicalize_homoglyph_latin_cbc():
    # CBC → expands via abbreviation map to общий анализ крови
    assert "общий анализ крови" in canonicalize("CBC")


def test_tokens_nonempty():
    assert tokens("УЗИ ОБП")  # expands and splits


# ── matcher ─────────────────────────────────────────────────────────────────
def test_exact_match_scores_one(matcher: Matcher):
    cands = matcher.match("Глюкоза")
    assert cands[0].service_id == "s4"
    assert cands[0].score == 1.0
    assert cands[0].method == "exact"


def test_abbreviation_matches_canonical(matcher: Matcher):
    cands = matcher.match("ОАК")
    assert cands[0].service_id == "s1"  # Общий анализ крови
    assert matcher.classify(cands[0].score) == "auto"


def test_typo_still_matches(matcher: Matcher):
    cands = matcher.match("Глюкза")
    assert cands[0].service_id == "s4"


def test_specialty_hint_disambiguates_duplicate_name(matcher: Matcher):
    # "Удаление папиллом" exists under Дерматология (s7) and Хирургия (s8).
    cands = matcher.match("Удаление папиллом", specialty_hint="Хирургия")
    assert cands[0].service_id == "s8"


def test_unrelated_string_is_unmatched_or_low(matcher: Matcher):
    cands = matcher.match("qwerty zxcvb")
    assert not cands or matcher.classify(cands[0].score) != "auto"


def test_top_k_limit(matcher: Matcher):
    cands = matcher.match("анализ", top_k=3)
    assert len(cands) <= 3
