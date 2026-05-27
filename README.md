# Churn-Aware Retention

> Predict which customers are about to churn, explain *why* with SHAP, and draft a personalised retention email grounded in those reasons. An adversarial LLM-as-judge grades every email before it reaches a human.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com/)
[![XGBoost](https://img.shields.io/badge/XGBoost-2.1-orange.svg)](https://xgboost.readthedocs.io/)
[![MLflow](https://img.shields.io/badge/MLflow-2.18-0194E2.svg)](https://mlflow.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## What it does

Most "AI for retention" tools either send generic LLM-drafted emails ("we miss you!") or fall back on rule-based templates. Both miss the point — a retention email is only useful if it speaks to the *specific reasons* a customer is at risk.

This system does the chain end to end:

1. **Classical ML** predicts churn probability for every customer.
2. **SHAP** quantifies which features drove each prediction.
3. **An LLM** drafts a retention email grounded in those specific risk factors, optionally querying the database for concrete supporting numbers (this customer's actual delivery time, their recent reviews, the marketplace baseline).
4. **An adversarial LLM-as-judge** scores every draft, persists its reasoning + per-clause verdicts, and flags the recurring weaknesses.

A React dashboard surfaces all of it — triage inbox, pipeline DAG, judge-insights viz — and a single **Run pipeline** button drives the whole chain.

---

## Data

The dataset is the [Olist Brazilian e-commerce dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) — ~100K orders across 9 related tables.

**Churn label.** Olist ships no churn labels, so the project defines its own: as of a snapshot date, a customer is churned if they place no order in the next 180 days. Features only use events on or before that snapshot, so the label is leakage-free.

**Synthetic augmentation.** Olist is a near-pure single-purchase marketplace (~3% repeat customers), so an honest future-window label would be ~98% positive and unlearnable. A signal-driven simulation adds synthetic repeat orders whose timing depends on each customer's *real* first-order experience (review score, delivery speed). The training set is presented as **Olist augmented with simulation**, never as raw Olist.

---

## Architecture

Postgres medallion warehouse → XGBoost → LLM → LLM-as-judge. dbt builds the silver/gold layers; Dagster orchestrates the full chain nightly; FastAPI exposes the same chain on demand from the dashboard.

```
raw / synthetic schemas (Olist + simulated repeat orders)
                  │
                  ▼  dbt staging views (silver) → customer_features (gold)
                  │
                  ▼  XGBoost classifier — registered in MLflow
                  │
                  ▼  serving.predictions + serving.shap_values
                  │
                  ▼  retention_emails — Claude haiku-4-5, tool-augmented
                  │
                  ▼  eval_scores — adversarial LLM-as-judge
```

The architectural choice that matters: **the ML model's SHAP output becomes structured input to the LLM prompt, and the judge's structured output becomes feedback the dashboard can visualise.**

---

## Tech Stack

| Layer | Technology |
|---|---|
| Warehouse | Postgres 16 (medallion: raw / analytics / serving) |
| Transformation | dbt — SQL models with built-in tests and lineage |
| Orchestration | Dagster — dbt models as observable assets + nightly schedule |
| ML | XGBoost + SHAP (registered in MLflow) |
| LLM | Anthropic Claude `claude-haiku-4-5` — tool use, JSON-schema structured output, prompt caching, async fan-out |
| API | FastAPI |
| Frontend | React + TypeScript + Tailwind (Vite) |
| Local infra | Docker Compose (Postgres) |

---

## Quick Start

### Prerequisites
- Python 3.11+
- Docker (for the local Postgres)
- The Olist dataset zip at `data/raw_data.zip` (free from Kaggle, ~45 MB)
- An Anthropic API key in `.env` (for the LLM steps)

### Run the data pipeline

```bash
pip install -e .                               # backend + deps
docker compose up -d                           # local Postgres 16

unzip data/raw_data.zip -d data/raw            # extract the 9 Olist CSVs

PYTHONPATH=src python -m backend.db.loader.raw_loader         # CSVs → raw schema
PYTHONPATH=src python -m backend.db.simulation.repeat_orders  # synthetic repeat orders
dbt build --project-dir src/transform --profiles-dir src/transform  # silver + gold + tests
PYTHONPATH=src alembic upgrade head                           # serving tables
PYTHONPATH=src python -m backend.db.seed.display_names        # synthetic per-customer names
```

Explore the orchestration graph with `cd src/orchestration && dagster dev` (UI at `localhost:3000`).

### Run the dashboard

```bash
PYTHONPATH=src uvicorn backend.api.app:app --port 8000   # FastAPI backend
cd src/dashboard && npm install && npm run dev           # UI at localhost:5173
```

The split-button **Run pipeline ▾** in the top bar runs the full chain — `dbt rebuild → (retrain) → batch score → (LLM drafting) → (judge grading)` — and streams progress live. The dropdown toggles retrain and email generation independently and lets you set a custom Top-N for the email fan-out.

### Tests

```bash
pip install -e ".[dev]"   # installs pytest
pytest                    # ML + API unit tests, no DB required
```

---

## Key Results

### Data pipeline
- Snapshot date 2017-08-01, 180-day churn horizon
- Raw load: 9 Olist tables, ~1.5M rows
- Synthetic augmentation: ~58K repeat orders for 35% of customers
- Gold table: 18,618 customer feature snapshots, ~20 behavioural features
- Churn rate: 80.3% — a learnable target (a degenerate ~98% before augmentation)
- Split: deterministic, churn-stratified 70 / 15 / 15
- Signal: retained customers average a 4.81 review score and 9.5-day delivery; churned customers 3.88 and 13.7 days

### Churn model
- ROC-AUC: 0.79 test / 0.80 validation (no overfit)
- PR-AUC: 0.94 (inflated by the ~80% base rate — ROC-AUC is the honest headline)
- Decision threshold: 0.33 — tuned on validation PR to catch ≥85% of churners
- Precision / Recall @ 0.33: 0.87 / 0.86
- Top features: `avg_review_score`, `avg_delivery_days`, `recency_days`

### LLM generation + evaluation
- `claude-haiku-4-5` with tool use, structured output, prompt caching, async fan-out
- Generator may call any of four read-only DB tools (`get_customer_delivery_stats`, `get_customer_recent_orders`, `get_category_baseline`, `get_customer_review_history`) to ground claims in real customer history
- Every email is graded by the adversarial judge — score, certainty, reasoning, weaknesses, and per-clause verdicts persist to `serving.eval_scores`
- A dashboard **Judge insights** page rolls those up: score histogram, clause-verdict breakdown, recurring weakness phrases, per-email reasoning cards

The rubric is deliberately adversarial: default score 6, competent baseline 7, 10 essentially never awarded. Forced per-clause enumeration, mandatory ≥2 weaknesses per email, hard caps for prohibited tropes ("we miss you") and fabricated facts. It catches real generator bugs — wrong CTA intent, offer-when-prohibited, tone-vs-label disagreement — rather than rubber-stamping outputs.

---

## License

[MIT](LICENSE)

---

## Acknowledgments

- Olist Brazilian E-commerce dataset by Olist via Kaggle
- SHAP library by Scott Lundberg

---

<sub>Built by [@jhatch3](https://github.com/jhatch3). If this was useful, star the repo or [reach out](mailto:jjhatch03@gmail.com).</sub>
