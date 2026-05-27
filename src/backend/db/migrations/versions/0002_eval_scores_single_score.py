"""drop per-dimension columns from eval_scores

Revision ID: 0002_eval_scores_single_score
Revises: 0001_initial
Create Date: 2026-05-18

The LLM-as-judge emits a single overall quality grade (1-5), so the four
per-dimension columns are removed. ``eval_scores`` now carries only
``overall_score`` + ``passed``.

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002_eval_scores_single_score"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# The four per-dimension score columns dropped by this migration.
_DIMENSION_COLUMNS = (
    "personalization",
    "tone_appropriateness",
    "cta_clarity",
    "length_appropriateness",
)


def upgrade() -> None:
    for column in _DIMENSION_COLUMNS:
        op.drop_column("eval_scores", column, schema="serving")


def downgrade() -> None:
    # Re-add the columns; a server_default lets the non-null constraint hold
    # against any existing rows.
    for column in _DIMENSION_COLUMNS:
        op.add_column(
            "eval_scores",
            sa.Column(
                column, sa.Float(), nullable=False, server_default=sa.text("0")
            ),
            schema="serving",
        )
        op.alter_column(
            "eval_scores", column, server_default=None, schema="serving"
        )
