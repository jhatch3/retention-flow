"""serving: performance indexes for the hot dashboard/pipeline queries

Revision ID: 0006_perf_indexes
Revises: 0005_generated_emails_tool_calls
Create Date: 2026-06-01

Adds the indexes the audit flagged as missing:
- predictions(churn_probability DESC) — every "top-N at risk" ORDER BY ... LIMIT
  (inbox queue, batch email selection, scoring/predictions overview) currently
  sorts the full table.
- generated_emails(generated_at DESC) — recent-emails list + the per-prediction
  "latest draft" lookup.
- shap_values(prediction_id) WHERE rank = 1 — partial index for the top-driver
  lookups in the inbox queue (one row per prediction, tiny).

The analytics.customer_features join-key index is added via a dbt post_hook on
the model itself (Alembic does not own the analytics schema).
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0006_perf_indexes"
down_revision: Union[str, None] = "0005_generated_emails_tool_calls"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_predictions_churn_probability",
        "predictions",
        ["churn_probability"],
        schema="serving",
        postgresql_ops={"churn_probability": "DESC"},
    )
    op.create_index(
        "ix_generated_emails_generated_at",
        "generated_emails",
        ["generated_at"],
        schema="serving",
        postgresql_ops={"generated_at": "DESC"},
    )
    op.create_index(
        "ix_shap_values_rank1",
        "shap_values",
        ["prediction_id"],
        schema="serving",
        postgresql_where="rank = 1",
    )


def downgrade() -> None:
    op.drop_index("ix_shap_values_rank1", table_name="shap_values", schema="serving")
    op.drop_index(
        "ix_generated_emails_generated_at",
        table_name="generated_emails",
        schema="serving",
    )
    op.drop_index(
        "ix_predictions_churn_probability",
        table_name="predictions",
        schema="serving",
    )
