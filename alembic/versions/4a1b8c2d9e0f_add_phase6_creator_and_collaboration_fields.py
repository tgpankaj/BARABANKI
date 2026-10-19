"""add_phase6_creator_and_collaboration_fields

Revision ID: 4a1b8c2d9e0f
Revises: 3ef4d8ed794e
Create Date: 2026-10-18 22:55:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4a1b8c2d9e0f'
down_revision: Union[str, Sequence[str], None] = '3ef4d8ed794e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    def get_columns(tbl):
        if tbl not in existing_tables:
            return []
        return [c["name"] for c in inspector.get_columns(tbl)]

    # 1. Column additions for creator_profiles
    if "creator_profiles" in existing_tables:
        creator_cols = get_columns("creator_profiles")
        with op.batch_alter_table("creator_profiles", schema=None) as batch_op:
            if "locality" not in creator_cols:
                batch_op.add_column(sa.Column("locality", sa.String(length=100), server_default="Barabanki", nullable=False))
            if "languages" not in creator_cols:
                batch_op.add_column(sa.Column("languages", sa.String(length=150), server_default="Hindi, Awadhi", nullable=True))
            if "content_categories" not in creator_cols:
                batch_op.add_column(sa.Column("content_categories", sa.String(length=255), nullable=True))
            if "profile_photo" not in creator_cols:
                batch_op.add_column(sa.Column("profile_photo", sa.String(length=500), nullable=True))
            if "facebook" not in creator_cols:
                batch_op.add_column(sa.Column("facebook", sa.String(length=255), nullable=True))
            if "linkedin" not in creator_cols:
                batch_op.add_column(sa.Column("linkedin", sa.String(length=255), nullable=True))
            if "twitter_x" not in creator_cols:
                batch_op.add_column(sa.Column("twitter_x", sa.String(length=255), nullable=True))
            if "is_verified" not in creator_cols:
                batch_op.add_column(sa.Column("is_verified", sa.Boolean(), server_default=sa.text("false"), nullable=False))
            if "verification_badge" not in creator_cols:
                batch_op.add_column(sa.Column("verification_badge", sa.String(length=60), nullable=True))
            if "verification_notes" not in creator_cols:
                batch_op.add_column(sa.Column("verification_notes", sa.Text(), nullable=True))
            if "profile_views" not in creator_cols:
                batch_op.add_column(sa.Column("profile_views", sa.Integer(), server_default=sa.text("0"), nullable=False))
            if "updated_at" not in creator_cols:
                batch_op.add_column(sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False))

    # 2. Table: business_collaborations
    if "business_collaborations" not in existing_tables:
        op.create_table(
            "business_collaborations",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("business_id", sa.Integer(), nullable=False),
            sa.Column("creator_id", sa.Integer(), nullable=False),
            sa.Column("sender_user_id", sa.Integer(), nullable=False),
            sa.Column("campaign_title", sa.String(length=150), nullable=False),
            sa.Column("campaign_description", sa.Text(), nullable=False),
            sa.Column("proposed_deliverables", sa.Text(), nullable=False),
            sa.Column("start_date", sa.String(length=50), nullable=True),
            sa.Column("end_date", sa.String(length=50), nullable=True),
            sa.Column("budget_range", sa.String(length=80), nullable=True),
            sa.Column("contact_preference", sa.String(length=50), server_default="email", nullable=False),
            sa.Column("contact_details", sa.String(length=150), nullable=False),
            sa.Column("status", sa.String(length=30), server_default="pending", nullable=False),
            sa.Column("creator_response_notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["creator_id"], ["creator_profiles.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["sender_user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_business_collaborations_id"), "business_collaborations", ["id"], unique=False)
        op.create_index(op.f("ix_business_collaborations_business_id"), "business_collaborations", ["business_id"], unique=False)
        op.create_index(op.f("ix_business_collaborations_creator_id"), "business_collaborations", ["creator_id"], unique=False)
        op.create_index(op.f("ix_business_collaborations_sender_user_id"), "business_collaborations", ["sender_user_id"], unique=False)
        op.create_index(op.f("ix_business_collaborations_status"), "business_collaborations", ["status"], unique=False)


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    if "business_collaborations" in existing_tables:
        op.drop_table("business_collaborations")

    if "creator_profiles" in existing_tables:
        with op.batch_alter_table("creator_profiles", schema=None) as batch_op:
            batch_op.drop_column("updated_at")
            batch_op.drop_column("profile_views")
            batch_op.drop_column("verification_notes")
            batch_op.drop_column("verification_badge")
            batch_op.drop_column("is_verified")
            batch_op.drop_column("twitter_x")
            batch_op.drop_column("linkedin")
            batch_op.drop_column("facebook")
            batch_op.drop_column("profile_photo")
            batch_op.drop_column("content_categories")
            batch_op.drop_column("languages")
            batch_op.drop_column("locality")
