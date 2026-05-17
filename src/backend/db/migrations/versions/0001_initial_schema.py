"""initial serving schema: predictions, shap_values, generated_emails, eval_scores

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-16

Alembic owns only the `serving` schema (the application's write model). The
`raw` schema is created by the one-time CSV loader; the `analytics` schema and
its tables/views are created by dbt.

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Enum types live in the `serving` schema alongside the tables that use them.
email_status = postgresql.ENUM(
    "draft", "approved", "sent", "rejected",
    name="email_status", schema="serving", create_type=False,
)
evaluator = postgresql.ENUM(
    "distilbert", "llm_judge",
    name="evaluator", schema="serving", create_type=False,
)


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS serving")
    bind = op.get_bind()
    email_status.create(bind, checkfirst=True)
    evaluator.create(bind, checkfirst=True)

    op.create_table(
        "predictions",
        sa.Column("id", sa.Integer(), nullable=False),
        # Natural-key reference to the dbt-managed gold table (no FK).
        sa.Column("customer_unique_id", sa.String(length=64), nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("model_version", sa.String(length=64), nullable=False),
        sa.Column("churn_probability", sa.Float(), nullable=False),
        sa.Column(
            "threshold", sa.Float(), server_default=sa.text("0.5"), nullable=False
        ),
        sa.Column("predicted_label", sa.Boolean(), nullable=False),
        sa.Column("base_value", sa.Float(), nullable=True),
        sa.Column("inference_latency_ms", sa.Float(), nullable=True),
        sa.Column(
            "predicted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_predictions"),
        schema="serving",
    )
    op.create_index(
        "ix_predictions_customer_snapshot",
        "predictions",
        ["customer_unique_id", "snapshot_date"],
        schema="serving",
    )
    op.create_index(
        "ix_predictions_model_version", "predictions", ["model_version"],
        schema="serving",
    )
    op.create_index(
        "ix_predictions_predicted_at", "predictions", ["predicted_at"],
        schema="serving",
    )

    op.create_table(
        "shap_values",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("prediction_id", sa.Integer(), nullable=False),
        sa.Column("feature_name", sa.String(length=128), nullable=False),
        sa.Column("feature_value", sa.Float(), nullable=True),
        sa.Column("shap_value", sa.Float(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_shap_values"),
        sa.ForeignKeyConstraint(
            ["prediction_id"], ["serving.predictions.id"],
            name="fk_shap_values_prediction_id_predictions", ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "prediction_id", "feature_name", name="uq_shap_values_prediction_id"
        ),
        schema="serving",
    )
    op.create_index(
        "ix_shap_values_prediction_id", "shap_values", ["prediction_id"],
        schema="serving",
    )

    op.create_table(
        "generated_emails",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("prediction_id", sa.Integer(), nullable=False),
        sa.Column("subject", sa.String(length=256), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("model", sa.String(length=64), nullable=False),
        sa.Column(
            "status", email_status,
            server_default=sa.text("'draft'"), nullable=False,
        ),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("cached_tokens", sa.Integer(), nullable=True),
        sa.Column("cost_usd", sa.Numeric(precision=8, scale=5), nullable=True),
        sa.Column("latency_ms", sa.Float(), nullable=True),
        sa.Column(
            "generated_at", sa.DateTime(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_generated_emails"),
        sa.ForeignKeyConstraint(
            ["prediction_id"], ["serving.predictions.id"],
            name="fk_generated_emails_prediction_id_predictions",
            ondelete="CASCADE",
        ),
        schema="serving",
    )
    op.create_index(
        "ix_generated_emails_prediction_id", "generated_emails",
        ["prediction_id"], schema="serving",
    )
    op.create_index(
        "ix_generated_emails_status", "generated_emails", ["status"],
        schema="serving",
    )

    op.create_table(
        "eval_scores",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email_id", sa.Integer(), nullable=False),
        sa.Column("evaluator", evaluator, nullable=False),
        sa.Column("personalization", sa.Float(), nullable=False),
        sa.Column("tone_appropriateness", sa.Float(), nullable=False),
        sa.Column("cta_clarity", sa.Float(), nullable=False),
        sa.Column("length_appropriateness", sa.Float(), nullable=False),
        sa.Column("overall_score", sa.Float(), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("judge_model", sa.String(length=64), nullable=True),
        sa.Column("latency_ms", sa.Float(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_eval_scores"),
        sa.ForeignKeyConstraint(
            ["email_id"], ["serving.generated_emails.id"],
            name="fk_eval_scores_email_id_generated_emails", ondelete="CASCADE",
        ),
        sa.UniqueConstraint("email_id", "evaluator", name="uq_eval_scores_email_id"),
        schema="serving",
    )
    op.create_index(
        "ix_eval_scores_email_id", "eval_scores", ["email_id"], schema="serving",
    )


def downgrade() -> None:
    op.drop_table("eval_scores", schema="serving")
    op.drop_table("generated_emails", schema="serving")
    op.drop_table("shap_values", schema="serving")
    op.drop_table("predictions", schema="serving")

    bind = op.get_bind()
    evaluator.drop(bind, checkfirst=True)
    email_status.drop(bind, checkfirst=True)

    op.execute("DROP SCHEMA IF EXISTS serving")
