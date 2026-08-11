"""add auth email code and password reset state

Revision ID: 20260521_auth_email_password_reset
Revises: eaea74f5ce71
Create Date: 2026-05-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260521_auth_email_password_reset"
down_revision: Union[str, Sequence[str], None] = "eaea74f5ce71"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema for real account verification and password reset."""
    op.add_column(
        "users",
        sa.Column("is_email_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("users", sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "email_verification_codes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("purpose", sa.String(length=32), nullable=False),
        sa.Column("code_hash", sa.String(length=128), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_email_verification_codes_email"), "email_verification_codes", ["email"], unique=False)
    op.create_index(op.f("ix_email_verification_codes_id"), "email_verification_codes", ["id"], unique=False)
    op.create_index(op.f("ix_email_verification_codes_purpose"), "email_verification_codes", ["purpose"], unique=False)
    op.create_index(op.f("ix_email_verification_codes_user_id"), "email_verification_codes", ["user_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_email_verification_codes_user_id"), table_name="email_verification_codes")
    op.drop_index(op.f("ix_email_verification_codes_purpose"), table_name="email_verification_codes")
    op.drop_index(op.f("ix_email_verification_codes_id"), table_name="email_verification_codes")
    op.drop_index(op.f("ix_email_verification_codes_email"), table_name="email_verification_codes")
    op.drop_table("email_verification_codes")

    op.drop_column("users", "last_login_at")
    op.drop_column("users", "password_changed_at")
    op.drop_column("users", "is_email_verified")
