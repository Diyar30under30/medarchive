"""Price versioning tests (brief §10, §18): newer-dated row supersedes the prior,
history retained with correct active flags."""
from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
import app.models  # noqa: F401
from app.models.partner import Partner
from app.models.service import Service
from app.models.price_item import PriceItem
from app.versioning.history import apply_versioning, latest_active


@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    s.add(Partner(partner_id="p1", name="Clinic"))
    s.add(Service(service_id="s1", service_name="Глюкоза", category="Биохимия", synonyms=[]))
    s.commit()
    yield s
    s.close()


def _item(item_id, price, eff):
    return PriceItem(
        item_id=item_id, doc_id="d", partner_id="p1", service_name_raw="Глюкоза",
        service_id="s1", price_resident_kzt=price, effective_date=eff, is_active=True,
    )


def test_newer_supersedes_older(db):
    old = _item("i1", 1500, date(2024, 1, 1))
    db.add(old); db.flush()
    apply_versioning(db, old)

    new = _item("i2", 1800, date(2024, 6, 1))
    db.add(new); db.flush()
    apply_versioning(db, new)
    db.commit()

    db.refresh(old); db.refresh(new)
    assert old.is_active is False
    assert old.superseded_by == "i2"
    assert new.is_active is True
    assert latest_active(db, "p1", "s1").item_id == "i2"


def test_older_arriving_late_is_archived(db):
    new = _item("i2", 1800, date(2024, 6, 1))
    db.add(new); db.flush()
    apply_versioning(db, new)

    # An older-dated document ingested afterwards must not override the newer price.
    old = _item("i1", 1500, date(2024, 1, 1))
    db.add(old); db.flush()
    apply_versioning(db, old)
    db.commit()

    db.refresh(old); db.refresh(new)
    assert new.is_active is True
    assert old.is_active is False
    assert latest_active(db, "p1", "s1").item_id == "i2"
