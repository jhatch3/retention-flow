"""customer_display_names — synthetic human-readable labels per customer

Revision ID: 0003_customer_display_names
Revises: 0002_eval_scores_single_score
Create Date: 2026-05-27

Olist customer_unique_ids are 32-char anonymised hashes. The dashboard wants a
friendlier label per customer for the inbox queue + per-customer detail. A
small mapping table holds a deterministic synthetic display name per
``customer_unique_id``. Populated by ``src/backend/db/seed/display_names.py``;
not produced by dbt because the value is presentation-only.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003_customer_display_names"
down_revision: Union[str, None] = "0002_eval_scores_single_score"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "customer_display_names",
        sa.Column("customer_unique_id", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint(
            "customer_unique_id", name="pk_customer_display_names"
        ),
        schema="serving",
    )


def downgrade() -> None:
    op.drop_table("customer_display_names", schema="serving")
