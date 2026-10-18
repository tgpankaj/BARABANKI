"""add_phase3_models_and_columns

Revision ID: 3ef4d8ed794e
Revises: 8c5c6da4cdf8
Create Date: 2026-10-18 08:25:45.535025

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3ef4d8ed794e'
down_revision: Union[str, Sequence[str], None] = '8c5c6da4cdf8'
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

    # 1. Column additions for existing tables
    user_cols = get_columns("users")
    if "locality" not in user_cols:
        with op.batch_alter_table("users", schema=None) as batch_op:
            batch_op.add_column(sa.Column("locality", sa.String(length=100), server_default="Barabanki", nullable=False))

    post_cols = get_columns("community_posts")
    if "image_url" not in post_cols:
        with op.batch_alter_table("community_posts", schema=None) as batch_op:
            batch_op.add_column(sa.Column("image_url", sa.String(length=500), nullable=True))

    event_cols = get_columns("events")
    if "capacity" not in event_cols:
        with op.batch_alter_table("events", schema=None) as batch_op:
            batch_op.add_column(sa.Column("capacity", sa.Integer(), nullable=True))

    report_cols = get_columns("reports")
    if "moderator_id" not in report_cols:
        with op.batch_alter_table("reports", schema=None) as batch_op:
            batch_op.add_column(sa.Column("moderator_id", sa.Integer(), nullable=True))
            batch_op.create_foreign_key("fk_reports_moderator_id", "users", ["moderator_id"], ["id"], ondelete="SET NULL")

    if "moderator_notes" not in report_cols:
        with op.batch_alter_table("reports", schema=None) as batch_op:
            batch_op.add_column(sa.Column("moderator_notes", sa.Text(), nullable=True))

    # 2. Table: post_likes
    if "post_likes" not in existing_tables:
        op.create_table(
            "post_likes",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("post_id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["post_id"], ["community_posts.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("post_id", "user_id", name="uq_post_like_user_post"),
        )
        with op.batch_alter_table("post_likes", schema=None) as batch_op:
            batch_op.create_index(batch_op.f("ix_post_likes_id"), ["id"], unique=False)
            batch_op.create_index(batch_op.f("ix_post_likes_post_id"), ["post_id"], unique=False)
            batch_op.create_index(batch_op.f("ix_post_likes_user_id"), ["user_id"], unique=False)

    # 3. Table: user_follows
    if "user_follows" not in existing_tables:
        op.create_table(
            "user_follows",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("follower_id", sa.Integer(), nullable=False),
            sa.Column("following_id", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["follower_id"], ["users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["following_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("follower_id", "following_id", name="uq_user_follow_pair"),
        )
        with op.batch_alter_table("user_follows", schema=None) as batch_op:
            batch_op.create_index(batch_op.f("ix_user_follows_id"), ["id"], unique=False)
            batch_op.create_index(batch_op.f("ix_user_follows_follower_id"), ["follower_id"], unique=False)
            batch_op.create_index(batch_op.f("ix_user_follows_following_id"), ["following_id"], unique=False)

    # 4. Table: event_registrations
    if "event_registrations" not in existing_tables:
        op.create_table(
            "event_registrations",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("event_id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(length=30), nullable=False),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("event_id", "user_id", name="uq_event_registration_user_event"),
        )
        with op.batch_alter_table("event_registrations", schema=None) as batch_op:
            batch_op.create_index(batch_op.f("ix_event_registrations_id"), ["id"], unique=False)
            batch_op.create_index(batch_op.f("ix_event_registrations_event_id"), ["event_id"], unique=False)
            batch_op.create_index(batch_op.f("ix_event_registrations_user_id"), ["user_id"], unique=False)
            batch_op.create_index(batch_op.f("ix_event_registrations_status"), ["status"], unique=False)

    # 5. Table: notifications
    if "notifications" not in existing_tables:
        op.create_table(
            "notifications",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("recipient_id", sa.Integer(), nullable=False),
            sa.Column("sender_id", sa.Integer(), nullable=True),
            sa.Column("notification_type", sa.String(length=50), nullable=False),
            sa.Column("title", sa.String(length=200), nullable=False),
            sa.Column("message", sa.Text(), nullable=False),
            sa.Column("link", sa.String(length=255), nullable=True),
            sa.Column("is_read", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["recipient_id"], ["users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["sender_id"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        with op.batch_alter_table("notifications", schema=None) as batch_op:
            batch_op.create_index(batch_op.f("ix_notifications_id"), ["id"], unique=False)
            batch_op.create_index(batch_op.f("ix_notifications_recipient_id"), ["recipient_id"], unique=False)
            batch_op.create_index(batch_op.f("ix_notifications_is_read"), ["is_read"], unique=False)
            batch_op.create_index(batch_op.f("ix_notifications_created_at"), ["created_at"], unique=False)

    # 6. Table: civic_issues
    if "civic_issues" not in existing_tables:
        op.create_table(
            "civic_issues",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("title", sa.String(length=200), nullable=False),
            sa.Column("slug", sa.String(length=220), nullable=False),
            sa.Column("category", sa.String(length=50), nullable=False),
            sa.Column("locality", sa.String(length=100), nullable=False),
            sa.Column("landmark", sa.String(length=150), nullable=True),
            sa.Column("latitude", sa.Float(), nullable=True),
            sa.Column("longitude", sa.Float(), nullable=True),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("image_url", sa.String(length=500), nullable=True),
            sa.Column("status", sa.String(length=30), nullable=False),
            sa.Column("upvotes", sa.Integer(), nullable=False),
            sa.Column("admin_notes", sa.Text(), nullable=True),
            sa.Column("reported_by_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["reported_by_id"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        with op.batch_alter_table("civic_issues", schema=None) as batch_op:
            batch_op.create_index(batch_op.f("ix_civic_issues_id"), ["id"], unique=False)
            batch_op.create_index(batch_op.f("ix_civic_issues_slug"), ["slug"], unique=True)
            batch_op.create_index(batch_op.f("ix_civic_issues_category"), ["category"], unique=False)
            batch_op.create_index(batch_op.f("ix_civic_issues_locality"), ["locality"], unique=False)
            batch_op.create_index(batch_op.f("ix_civic_issues_status"), ["status"], unique=False)

    # 7. Table: civic_issue_upvotes
    if "civic_issue_upvotes" not in existing_tables:
        op.create_table(
            "civic_issue_upvotes",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("issue_id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["issue_id"], ["civic_issues.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("issue_id", "user_id", name="uq_issue_upvote_user_issue"),
        )
        with op.batch_alter_table("civic_issue_upvotes", schema=None) as batch_op:
            batch_op.create_index(batch_op.f("ix_civic_issue_upvotes_id"), ["id"], unique=False)
            batch_op.create_index(batch_op.f("ix_civic_issue_upvotes_issue_id"), ["issue_id"], unique=False)
            batch_op.create_index(batch_op.f("ix_civic_issue_upvotes_user_id"), ["user_id"], unique=False)

    # 8. Table: issue_status_history
    if "issue_status_history" not in existing_tables:
        op.create_table(
            "issue_status_history",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("issue_id", sa.Integer(), nullable=False),
            sa.Column("old_status", sa.String(length=30), nullable=False),
            sa.Column("new_status", sa.String(length=30), nullable=False),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("changed_by_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["changed_by_id"], ["users.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["issue_id"], ["civic_issues.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        with op.batch_alter_table("issue_status_history", schema=None) as batch_op:
            batch_op.create_index(batch_op.f("ix_issue_status_history_id"), ["id"], unique=False)
            batch_op.create_index(batch_op.f("ix_issue_status_history_issue_id"), ["issue_id"], unique=False)

    # 9. Table: moderation_audits
    if "moderation_audits" not in existing_tables:
        op.create_table(
            "moderation_audits",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("entity_type", sa.String(length=50), nullable=False),
            sa.Column("entity_id", sa.Integer(), nullable=False),
            sa.Column("moderator_id", sa.Integer(), nullable=True),
            sa.Column("action", sa.String(length=50), nullable=False),
            sa.Column("reason", sa.String(length=255), nullable=True),
            sa.Column("details", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["moderator_id"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        with op.batch_alter_table("moderation_audits", schema=None) as batch_op:
            batch_op.create_index(batch_op.f("ix_moderation_audits_id"), ["id"], unique=False)
            batch_op.create_index(batch_op.f("ix_moderation_audits_entity_type"), ["entity_type"], unique=False)
            batch_op.create_index(batch_op.f("ix_moderation_audits_entity_id"), ["entity_id"], unique=False)


def downgrade() -> None:
    op.drop_table("moderation_audits")
    op.drop_table("issue_status_history")
    op.drop_table("civic_issue_upvotes")
    op.drop_table("civic_issues")
    op.drop_table("notifications")
    op.drop_table("event_registrations")
    op.drop_table("user_follows")
    op.drop_table("post_likes")

    with op.batch_alter_table("reports", schema=None) as batch_op:
        batch_op.drop_column("moderator_notes")
        batch_op.drop_column("moderator_id")

    with op.batch_alter_table("events", schema=None) as batch_op:
        batch_op.drop_column("capacity")

    with op.batch_alter_table("community_posts", schema=None) as batch_op:
        batch_op.drop_column("image_url")

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("locality")
