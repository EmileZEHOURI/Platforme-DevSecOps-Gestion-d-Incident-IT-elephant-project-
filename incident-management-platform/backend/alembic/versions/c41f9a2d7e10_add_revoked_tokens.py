"""Durable JWT revocations.

Revision ID: c41f9a2d7e10
Revises: b7920b10f87c
"""
from alembic import op
import sqlalchemy as sa

revision = "c41f9a2d7e10"
down_revision = "b7920b10f87c"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("revoked_tokens", sa.Column("digest", sa.String(64), primary_key=True),
                    sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_revoked_tokens_expires_at", "revoked_tokens", ["expires_at"])


def downgrade():
    op.drop_index("ix_revoked_tokens_expires_at", table_name="revoked_tokens")
    op.drop_table("revoked_tokens")
