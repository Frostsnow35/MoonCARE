"""add conversation message meta

Revision ID: 20260603_conversation_message_meta
Revises: 20260525_music_feedback
Create Date: 2026-06-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260603_conversation_message_meta"
down_revision: Union[str, Sequence[str], None] = "20260525_music_feedback"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema with assistant message metadata."""
    op.add_column("conversations", sa.Column("message_meta", sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("conversations", "message_meta")
