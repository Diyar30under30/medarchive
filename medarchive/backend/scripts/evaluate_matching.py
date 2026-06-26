"""Evaluate the matcher over the ground-truth fixtures (brief §8).

Prints auto-match rate and precision so the headline ≥70% number can be proven
on stage. Run: python -m scripts.evaluate_matching
"""
from __future__ import annotations

from sqlalchemy import select

from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models.service import Service
from app.normalization.matcher import Matcher, ServiceIndex
import app.models  # noqa: F401
from scripts._fixture_data import RAW_TO_CANONICAL


def build_index(db) -> ServiceIndex:
    rows = [
        {
            "service_id": s.service_id,
            "service_name": s.service_name,
            "category": s.category,
            "synonyms": s.synonyms or [],
            "embedding": s.embedding,
        }
        for s in db.scalars(select(Service)).all()
    ]
    return ServiceIndex.from_rows(rows)


def main() -> int:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        if db.scalar(select(Service).limit(1)) is None:
            print("No services loaded — run `python -m scripts.load_reference` first.")
            return 1
        index = build_index(db)
        matcher = Matcher(index)

        total = len(RAW_TO_CANONICAL)
        auto = correct_auto = top1_correct = review = unmatched = 0

        print(f"\nEvaluating {total} raw→canonical pairs over {len(index)} services\n")
        print(f"{'RAW':<42} {'PRED':<34} {'score':>6} {'bucket':<9} ok")
        print("-" * 100)
        for raw, expected, hint in RAW_TO_CANONICAL:
            cands = matcher.match(raw, specialty_hint=hint, top_k=5)
            if not cands:
                unmatched += 1
                print(f"{raw[:40]:<42} {'<none>':<34} {0.0:>6} {'unmatched':<9} ✗")
                continue
            top = cands[0]
            bucket = matcher.classify(top.score)
            ok = top.service_name.strip() == expected.strip()
            if ok:
                top1_correct += 1
            if bucket == "auto":
                auto += 1
                if ok:
                    correct_auto += 1
            elif bucket == "review":
                review += 1
            else:
                unmatched += 1
            print(
                f"{raw[:40]:<42} {top.service_name[:32]:<34} {top.score:>6.2f} "
                f"{bucket:<9} {'✓' if ok else '✗'}"
            )

        auto_rate = auto / total if total else 0.0
        auto_precision = correct_auto / auto if auto else 0.0
        top1_acc = top1_correct / total if total else 0.0
        print("-" * 100)
        print(f"\nAuto-match rate     : {auto_rate:6.1%}  ({auto}/{total})  [target ≥70%]")
        print(f"Auto-match precision: {auto_precision:6.1%}  ({correct_auto}/{auto})")
        print(f"Top-1 accuracy      : {top1_acc:6.1%}  ({top1_correct}/{total})")
        print(f"Review queue        : {review}")
        print(f"Unmatched           : {unmatched}")
        print(f"Embeddings active   : {matcher.provider.available}\n")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
