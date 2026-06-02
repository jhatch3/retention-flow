"""generated_emails: persist the generator's tool-call log

Revision ID: 0005_generated_emails_tool_calls
Revises: 0004_eval_scores_reasoning
Create Date: 2026-06-01

The email generator runs a tool loop (querying the warehouse for real delivery
times, reviews, category baselines) but ``generate_top_n_emails`` discarded the
tool log, so the LLM-as-judge always received ``tool_calls: []`` in production.
That made the judge treat every tool-grounded number as a fabrication and cap
the score at <=5 — diverging from the test path, which passes the real tool
calls. This column persists the log so the judge sees the same payload in both
paths.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0005_generated_emails_tool_calls"
down_revision: Union[str, None] = "0004_eval_scores_reasoning"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "generated_emails",
        sa.Column(
            "tool_calls",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        schema="serving",
    )


def downgrade() -> None:
    op.drop_column("generated_emails", "tool_calls", schema="serving")
