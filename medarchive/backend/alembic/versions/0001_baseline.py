"""baseline schema

Creates the full MedArchive schema from the app's SQLAlchemy metadata so the
column types are dialect-correct: the `embedding` column becomes a real pgvector
`vector(384)` on PostgreSQL and `TEXT` (JSON) on SQLite — see app/db/types.py.
On PostgreSQL the pgvector extension is enabled first.

Revision ID: 0001_baseline
Revises:
Create Date: 2026-06-27
"""
from alembic import op

from app.db.base import Base
import app.models  # noqa: F401  (register all entities on Base.metadata)

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
