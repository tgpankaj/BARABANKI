"""add_phase7_advertising_tables

Revision ID: 5b2c9d3e8f1a
Revises: 4a1b8c2d9e0f
Create Date: 2026-10-18 23:35:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5b2c9d3e8f1a'
down_revision: Union[str, Sequence[str], None] = '4a1b8c2d9e0f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    # 1. ad_campaigns
    if "ad_campaigns" not in existing_tables:
        op.create_table(
            "ad_campaigns",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("business_id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=150), nullable=False),
            sa.Column("objective", sa.String(length=50), server_default="brand_awareness", nullable=False),
            sa.Column("headline", sa.String(length=100), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("image_url", sa.String(length=500), nullable=True),
            sa.Column("destination_url", sa.String(length=500), nullable=True),
            sa.Column("contact_action", sa.String(length=50), server_default="visit_website", nullable=False),
            sa.Column("contact_value", sa.String(length=100), nullable=True),
            sa.Column("placement", sa.String(length=50), server_default="homepage_sponsored", nullable=False),
            sa.Column("target_locality", sa.String(length=100), server_default="All Localities", nullable=False),
            sa.Column("target_category", sa.String(length=80), server_default="All Categories", nullable=False),
            sa.Column("start_date", sa.DateTime(), nullable=False),
            sa.Column("end_date", sa.DateTime(), nullable=False),
            sa.Column("pricing_plan", sa.String(length=50), server_default="starter_7days", nullable=False),
            sa.Column("budget_amount", sa.Float(), nullable=False),
            sa.Column("status", sa.String(length=30), server_default="pending_review", nullable=False),
            sa.Column("review_feedback", sa.Text(), nullable=True),
            sa.Column("reviewed_by_id", sa.Integer(), nullable=True),
            sa.Column("reviewed_at", sa.DateTime(), nullable=True),
            sa.Column("is_paused", sa.Boolean(), server_default=sa.text("false"), nullable=False),
            sa.Column("payment_status", sa.String(length=30), server_default="pending", nullable=False),
            sa.Column("impression_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
            sa.Column("click_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["reviewed_by_id"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_ad_campaigns_id"), "ad_campaigns", ["id"], unique=False)
        op.create_index(op.f("ix_ad_campaigns_business_id"), "ad_campaigns", ["business_id"], unique=False)
        op.create_index(op.f("ix_ad_campaigns_user_id"), "ad_campaigns", ["user_id"], unique=False)
        op.create_index(op.f("ix_ad_campaigns_placement"), "ad_campaigns", ["placement"], unique=False)
        op.create_index(op.f("ix_ad_campaigns_status"), "ad_campaigns", ["status"], unique=False)
        op.create_index(op.f("ix_ad_campaigns_payment_status"), "ad_campaigns", ["payment_status"], unique=False)

    # 2. ad_payments
    if "ad_payments" not in existing_tables:
        op.create_table(
            "ad_payments",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("campaign_id", sa.Integer(), nullable=False),
            sa.Column("business_id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("amount", sa.Float(), nullable=False),
            sa.Column("currency", sa.String(length=10), server_default="INR", nullable=False),
            sa.Column("payment_method", sa.String(length=50), server_default="upi_qr", nullable=False),
            sa.Column("gateway_provider", sa.String(length=50), server_default="manual_admin_verify", nullable=False),
            sa.Column("transaction_reference", sa.String(length=120), nullable=False),
            sa.Column("idempotency_key", sa.String(length=120), nullable=True),
            sa.Column("status", sa.String(length=30), server_default="proof_submitted", nullable=False),
            sa.Column("payment_proof_url", sa.String(length=500), nullable=True),
            sa.Column("verified_by_id", sa.Integer(), nullable=True),
            sa.Column("verified_at", sa.DateTime(), nullable=True),
            sa.Column("admin_notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["campaign_id"], ["ad_campaigns.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["verified_by_id"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_ad_payments_id"), "ad_payments", ["id"], unique=False)
        op.create_index(op.f("ix_ad_payments_campaign_id"), "ad_payments", ["campaign_id"], unique=False)
        op.create_index(op.f("ix_ad_payments_business_id"), "ad_payments", ["business_id"], unique=False)
        op.create_index(op.f("ix_ad_payments_user_id"), "ad_payments", ["user_id"], unique=False)
        op.create_index(op.f("ix_ad_payments_transaction_reference"), "ad_payments", ["transaction_reference"], unique=True)
        op.create_index(op.f("ix_ad_payments_idempotency_key"), "ad_payments", ["idempotency_key"], unique=True)
        op.create_index(op.f("ix_ad_payments_status"), "ad_payments", ["status"], unique=False)

    # 3. ad_impressions
    if "ad_impressions" not in existing_tables:
        op.create_table(
            "ad_impressions",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("campaign_id", sa.Integer(), nullable=False),
            sa.Column("placement", sa.String(length=50), nullable=False),
            sa.Column("viewer_ip", sa.String(length=64), nullable=True),
            sa.Column("user_id", sa.Integer(), nullable=True),
            sa.Column("session_id", sa.String(length=120), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["campaign_id"], ["ad_campaigns.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_ad_impressions_id"), "ad_impressions", ["id"], unique=False)
        op.create_index(op.f("ix_ad_impressions_campaign_id"), "ad_impressions", ["campaign_id"], unique=False)
        op.create_index(op.f("ix_ad_impressions_created_at"), "ad_impressions", ["created_at"], unique=False)

    # 4. ad_clicks
    if "ad_clicks" not in existing_tables:
        op.create_table(
            "ad_clicks",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("campaign_id", sa.Integer(), nullable=False),
            sa.Column("placement", sa.String(length=50), nullable=False),
            sa.Column("destination_url", sa.String(length=500), nullable=False),
            sa.Column("viewer_ip", sa.String(length=64), nullable=True),
            sa.Column("user_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["campaign_id"], ["ad_campaigns.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_ad_clicks_id"), "ad_clicks", ["id"], unique=False)
        op.create_index(op.f("ix_ad_clicks_campaign_id"), "ad_clicks", ["campaign_id"], unique=False)
        op.create_index(op.f("ix_ad_clicks_created_at"), "ad_clicks", ["created_at"], unique=False)

    # 5. ad_reports
    if "ad_reports" not in existing_tables:
        op.create_table(
            "ad_reports",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("campaign_id", sa.Integer(), nullable=False),
            sa.Column("reported_by_id", sa.Integer(), nullable=True),
            sa.Column("reporter_email", sa.String(length=100), nullable=True),
            sa.Column("reason", sa.String(length=80), nullable=False),
            sa.Column("details", sa.Text(), nullable=False),
            sa.Column("status", sa.String(length=30), server_default="pending", nullable=False),
            sa.Column("reviewed_by_id", sa.Integer(), nullable=True),
            sa.Column("admin_notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["campaign_id"], ["ad_campaigns.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["reported_by_id"], ["users.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["reviewed_by_id"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_ad_reports_id"), "ad_reports", ["id"], unique=False)
        op.create_index(op.f("ix_ad_reports_campaign_id"), "ad_reports", ["campaign_id"], unique=False)
        op.create_index(op.f("ix_ad_reports_status"), "ad_reports", ["status"], unique=False)


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    for tbl in ["ad_reports", "ad_clicks", "ad_impressions", "ad_payments", "ad_campaigns"]:
        if tbl in existing_tables:
            op.drop_table(tbl)
