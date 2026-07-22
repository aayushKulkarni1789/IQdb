"""add search session

Revision ID: 3a1b2c4d5e6f
Revises: 2f1e59d630a2
Create Date: 2026-07-19 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "3a1b2c4d5e6f"
down_revision = "2f1e59d630a2"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "searchsession",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("specs", postgresql.JSONB(), nullable=False),
        sa.Column("finalized", sa.Boolean(), nullable=False),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    op.drop_table("searchsession")
