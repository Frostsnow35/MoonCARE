"""add music feedback

Revision ID: 20260525_music_feedback
Revises: 20260521_auth_email_password_reset
Create Date: 2026-05-25 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260525_music_feedback"
down_revision: Union[str, Sequence[str], None] = "20260521_auth_email_password_reset"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema with music feedback records."""
    op.create_table(
        "music_feedback",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("music_id", sa.Integer(), nullable=True),
        sa.Column("music_title", sa.String(length=200), nullable=True),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("emotion_category", sa.String(length=50), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_music_feedback_action"), "music_feedback", ["action"], unique=False)
    op.create_index(op.f("ix_music_feedback_emotion_category"), "music_feedback", ["emotion_category"], unique=False)
    op.create_index(op.f("ix_music_feedback_id"), "music_feedback", ["id"], unique=False)
    op.create_index(op.f("ix_music_feedback_music_id"), "music_feedback", ["music_id"], unique=False)
    op.create_index(op.f("ix_music_feedback_user_id"), "music_feedback", ["user_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_music_feedback_user_id"), table_name="music_feedback")
    op.drop_index(op.f("ix_music_feedback_music_id"), table_name="music_feedback")
    op.drop_index(op.f("ix_music_feedback_id"), table_name="music_feedback")
    op.drop_index(op.f("ix_music_feedback_emotion_category"), table_name="music_feedback")
    op.drop_index(op.f("ix_music_feedback_action"), table_name="music_feedback")
    op.drop_table("music_feedback")
