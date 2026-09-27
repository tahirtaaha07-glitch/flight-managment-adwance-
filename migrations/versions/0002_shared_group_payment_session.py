"""Allow one Stripe checkout session to cover all itinerary holds.

Revision ID: 0002_group_payment_session
Revises: 0001_initial
"""
from alembic import op

revision = "0002_group_payment_session"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("seat_holds_payment_session_id_key", "seat_holds", type_="unique")
    op.create_index("ix_seat_holds_payment_session_id", "seat_holds", ["payment_session_id"])


def downgrade() -> None:
    op.drop_index("ix_seat_holds_payment_session_id", table_name="seat_holds")
    op.create_unique_constraint("seat_holds_payment_session_id_key", "seat_holds", ["payment_session_id"])
