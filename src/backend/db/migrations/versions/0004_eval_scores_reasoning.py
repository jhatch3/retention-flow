"""eval_scores: persist the judge's reasoning, weaknesses, clauses, certainty

Revision ID: 0004_eval_scores_reasoning
Revises: 0003_customer_display_names
Create Date: 2026-05-27

The LLM-as-judge already emits a structured grade (clauses_evaluated, weaknesses,
reasoning, certainty) but only ``overall_score`` + ``passed`` were persisted.
This migration adds JSONB columns so the dashboard can visualise the judge's
reasoning across all graded emails.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0004_eval_scores_reasoning"
down_revision: Union[str, None] = "0003_customer_display_names"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "eval_scores",
        sa.Column("certainty", sa.Float(), nullable=True),
        schema="serving",
    )
    op.add_column(
        "eval_scores",
        sa.Column("reasoning", sa.Text(), nullable=True),
        schema="serving",
    )
    op.add_column(
        "eval_scores",
        sa.Column(
            "weaknesses",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        schema="serving",
    )
    op.add_column(
        "eval_scores",
        sa.Column(
            "clauses_evaluated",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        schema="serving",
    )


def downgrade() -> None:
    op.drop_column("eval_scores", "clauses_evaluated", schema="serving")
    op.drop_column("eval_scores", "weaknesses", schema="serving")
    op.drop_column("eval_scores", "reasoning", schema="serving")
    op.drop_column("eval_scores", "certainty", schema="serving")
