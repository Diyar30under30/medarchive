"""String canonicalization for matching (brief §8.1).

Deterministic, dependency-free (pure stdlib + the abbreviation map) so it is
trivially unit-testable and identical across both runtime profiles.
"""
from __future__ import annotations

import re
import unicodedata

from app.normalization.abbreviations import ABBREVIATIONS, NOISE_QUALIFIERS

# Latin letters that look identical to Cyrillic ones — unify to Cyrillic so
# "CBC" vs "СВС" and Latin-typo'd Cyrillic words collapse together.
_HOMOGLYPHS = str.maketrans(
    {
        "a": "а", "e": "е", "o": "о", "p": "р", "c": "с", "y": "у", "x": "х",
        "k": "к", "m": "м", "t": "т", "h": "н", "b": "в",
    }
)

_PUNCT_RE = re.compile(r"[^\w\s]", flags=re.UNICODE)
_WS_RE = re.compile(r"\s+")
_NUM_NOISE_RE = re.compile(r"№\s*\d+")
# Spaced single-letter acronyms: "о а к" → "оак" so dotted forms (О.А.К.) expand.
_ACRONYM_RE = re.compile(r"\b(?:[^\W\d_]\s){1,}[^\W\d_]\b", flags=re.UNICODE)


def _collapse_acronyms(text: str) -> str:
    return _ACRONYM_RE.sub(lambda m: m.group(0).replace(" ", ""), text)


def _expand_abbreviations(text: str) -> str:
    # Multi-word keys first (longer keys win) to avoid partial clobbering.
    for key in sorted(ABBREVIATIONS, key=len, reverse=True):
        pattern = r"\b" + re.escape(key) + r"\b"
        text = re.sub(pattern, ABBREVIATIONS[key], text)
    return text


def strip_noise(text: str) -> tuple[str, list[str]]:
    """Remove noise qualifiers; return (cleaned, removed_features)."""
    removed: list[str] = []
    for q in NOISE_QUALIFIERS:
        pattern = r"\b" + re.escape(q) + r"\b"
        if re.search(pattern, text):
            removed.append(q)
            text = re.sub(pattern, " ", text)
    return _WS_RE.sub(" ", text).strip(), removed


def canonicalize(raw: str, *, expand: bool = True, drop_noise: bool = True) -> str:
    """Full canonical form used as the matching key."""
    if raw is None:
        return ""
    text = unicodedata.normalize("NFKC", str(raw)).lower().strip()
    text = _NUM_NOISE_RE.sub(" ", text)
    # Strip punctuation BEFORE expanding so dotted/slashed abbreviations
    # ("кл. ан. крови", "б/х") collapse onto their map keys.
    text = _PUNCT_RE.sub(" ", text)
    text = _WS_RE.sub(" ", text).strip()
    text = _collapse_acronyms(text)
    # Expand abbreviations BEFORE homoglyph unification, otherwise Latin
    # abbreviations (cbc, tsh, pcr) get transliterated to Cyrillic first and
    # never match their keys.
    if expand:
        text = _expand_abbreviations(text)
    text = text.translate(_HOMOGLYPHS)
    text = _WS_RE.sub(" ", text).strip()
    if drop_noise:
        text, _ = strip_noise(text)
    return text


def tokens(raw: str) -> list[str]:
    return canonicalize(raw).split()
