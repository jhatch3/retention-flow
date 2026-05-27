# Churn-Aware Retention

> Production-grade ML + LLM system that predicts customer churn from raw e-commerce data, explains *why* with SHAP, and generates grounded retention emails.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com/)
[![XGBoost](https://img.shields.io/badge/XGBoost-2.1-orange.svg)](https://xgboost.readthedocs.io/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.5-EE4C2C.svg)](https://pytorch.org/)
[![MLflow](https://img.shields.io/badge/MLflow-2.18-0194E2.svg)](https://mlflow.org/)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED.svg)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![CI](https://img.shields.io/badge/CI-passing-brightgreen.svg)](#)

A reference implementation of the **ML→LLM handoff pattern**: classical ML predicts customer churn from raw transactional data, SHAP explains the prediction, and an LLM generates a personalized retention email grounded in those specific risk factors. Output quality is validated by a two-tier eval framework pairing a fine-tuned DistilBERT classifier with LLM-as-judge scoring.

Built on real e-commerce data with a custom-defined churn label, not a pre-labeled tutorial dataset.

---

## Table of Contents

- [Overview](#overview)
- [Data](#data)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Key Results](#key-results)
- [Quick Start](#quick-start)
- [The ML→LLM Handoff](#the-mlllm-handoff)
- [Evaluation Framework](#evaluation-framework)
- [Engineering Decisions](#engineering-decisions)
- [Project Structure](#project-structure)
- [Documentation](#documentation)
- [Roadmap](#roadmap)
- [License](#license)

---

## Overview

Most "AI for retention" systems either send generic LLM-drafted emails ("we miss you!") or rely on rule-based templates. Both miss the point: a retention email is only useful if it addresses the *specific reasons* a customer is at risk.

This project implements the architectural pattern most production teams converge on:

1. **Classical ML** predicts churn probability for each customer
2. **SHAP** quantifies which features drove each prediction
3. **Structured context** flows from the model's explanation into an LLM prompt
4. **The LLM** generates an email grounded in that customer's specific risk factors
5. **Evaluation** scores every generated email before it goes out

The result is a system where retention emails address real, customer-specific concerns instead of pattern-matching against generic playbooks.

---

## Data

This project builds on the [Olist Brazilian E-commerce dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) — ~100K orders across 9 related tables. **No churn labels exist in the source data**, and Olist is a near-pure single-purchase marketplace: only ~3% of customers ever place a second order.

### Churn definition

Churn is a **future-window label**: as of a snapshot date, a customer is churned if they place no order in the following 180 days. Features use only events on or before the snapshot date, so the label is leakage-free. An earlier "gap since last order" definition was rejected — it leaks, because recency would be both a feature and (by construction) the label. See [`docs/adr/0002-future-window-churn-label.md`](docs/adr/0002-future-window-churn-label.md).

### Synthetic augmentation

With only ~3% repeat customers, an honest future-window label is ~98% positive — degenerate, with no signal to learn. A one-time, **signal-driven simulation** adds synthetic repeat orders: each customer's reorder propensity is a function of their *real* first-order experience (review score, delivery speed). Churn becomes a learnable target without fabricating the relationship blindly. The training data is therefore **Olist augmented with simulation**, and metrics are reported as such. See [`docs/adr/0004-synthetic-repeat-order-augmentation.md`](docs/adr/0004-synthetic-repeat-order-augmentation.md).

### Medallion pipeline

A one-time loader copies the 9 CSVs verbatim into a `raw` Postgres schema; the simulation writes synthetic orders into a `synthetic` schema. dbt then transforms both — staging views (silver) feeding the gold table `customer_features`. The transformations run as a nightly Dagster asset graph.

---

## Architecture

The data pipeline is a **medallion architecture in Postgres**, orchestrated by Dagster:

```
data/raw/*.csv ──one-time loader (COPY)──┐
                                         ▼
┌──────────────────────────────────────────────────────────────────┐
│ raw        9 Olist tables (verbatim)                              │
│ synthetic  simulated repeat orders                                │
└───────────────────────────┬──────────────────────────────────────┘
              dbt staging views — clean / type / dedupe / union
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│ analytics  stg_* views (silver)  →  customer_features (gold table)│
└───────────────────────────┬──────────────────────────────────────┘
                            ▼
       churn_model — XGBoost, retrained nightly, registered in MLflow
                            │
             LLM / eval services consume predictions (roadmap)
```

- **raw** — 9 Olist tables loaded once; `synthetic` holds simulated repeat orders.
- **analytics** — dbt-owned: staging views (silver) and the gold table `customer_features`.

Dagster runs the dbt transformations and the churn-model retraining as one nightly asset graph (dbt models → assets, dbt tests → asset checks, then the model registered in MLflow). Full decisions in [`docs/adr/`](docs/adr/) and the domain glossary in [`CONTEXT.md`](CONTEXT.md).

The architectural choice that matters: **the ML model's interpretability output (SHAP values) becomes structured input to the LLM's prompt.** That handoff is the project.

---

## Tech Stack

| Layer | Technology | Why |
|---|---|---|
| Data warehouse | Postgres 16 (medallion: raw / analytics) | One queryable source of truth for the pipeline |
| Transformation | dbt | SQL models with built-in tests and lineage; staging (silver) → gold |
| Orchestration | Dagster | dbt models as observable assets; nightly scheduled runs |
| ML model | XGBoost + SHAP | Industry standard for tabular classification with explainability |
| Deep learning | DistilBERT (PyTorch + Hugging Face) | Fine-tuned for inline email quality classification |
| LLM | Anthropic Claude (`claude-haiku-4-5`) | Tool use + `output_config` JSON-schema-enforced structured outputs; ephemeral-cache markers on long system prompts |
| API framework | FastAPI + Pydantic | Type-safe contracts end-to-end, async LLM calls |
| MLOps | MLflow | Model registry, experiment tracking, version control |
| Observability | structlog | JSON-structured logs with request IDs and cost tracking |
| Deployment | Docker + AWS App Runner | Single-service deployment without Kubernetes overhead |
| CI/CD | GitHub Actions | Lint, test, build, push to ECR, deploy on merge |

Every choice is documented in [Engineering Decisions](#engineering-decisions).

---

## Key Results

### Data pipeline (measured)

Snapshot date 2017-08-01, 180-day churn horizon.

- **Raw load**: 9 Olist tables, ~1.5M rows copied into Postgres
- **Synthetic augmentation**: ~58K repeat orders for 35% of customers (signal-driven)
- **Gold table**: 18,618 customer feature snapshots, ~20 behavioral features
- **Churn rate**: 80.3% — a learnable target (a degenerate ~98% before augmentation)
- **Split**: deterministic, churn-stratified 70 / 15 / 15 train / test / validation
- **Signal**: retained customers average a 4.81 review score and 9.5-day delivery; churned customers 3.88 and 13.7 days
- **dbt**: 8 models, 18 data tests — all passing

### ML model (measured)

XGBoost churn classifier, trained on the gold table, registered in MLflow.

- **ROC-AUC**: 0.79 test / 0.80 validation
- **PR-AUC**: 0.94 (inflated by the ~80% churn base rate — ROC-AUC is the honest headline)
- **Decision threshold**: 0.33 — tuned on the validation PR curve to catch ≥85% of churners
- **Precision / Recall** (test, @0.33): 0.87 / 0.86
- **Brier score**: 0.18
- **Top features**: `avg_review_score`, `avg_delivery_days`, `recency_days` — the model recovers the signal the synthetic augmentation injected
- test ≈ validation — no overfitting

### LLM generation + evaluation

Implemented in `src/ai/` against `claude-haiku-4-5`. Generation flow per customer:

1. Customer payload (`customer_id`, `churn_probability`, `risk_tier`, top-5 SHAP factors, `customer_context`) becomes the user message.
2. Claude may call any of four read-only DB tools during composition — `get_customer_delivery_stats`, `get_customer_recent_orders`, `get_category_baseline`, `get_customer_review_history` — to ground claims in real customer history rather than aggregate SHAP values alone.
3. The model emits a single JSON object via Anthropic's `output_config` (json_schema), enforced at the API boundary: `subject`, `body`, `tone`, `includes_offer`, `call_to_action.intent`, `grounding.shap_factors_addressed`, `grounding.factors_intentionally_ignored`, and a `reasoning` field.

Every email is then graded by an **adversarial LLM-as-judge** (`src/ai/grader.py`) with its own cached system prompt, structured output, and the generator's tool-call log forwarded into the grade payload (so the judge can verify cited numbers against real tool outputs before applying the fabrication hard-cap). The rubric uses calibration anchors (default 6, competent baseline 7, 10 essentially never awarded), forces per-clause enumeration with an enum-typed verdict (`met` / `partially_met` / `not_met` / `not_assessable`), and requires the judge to surface at least two specific weaknesses per email.

#### Latest run — 6 real-customer test cases across all four risk tiers

| Test case | Score | Certainty | Tools | Clauses (met / partial / missed) |
|---|---:|---:|---:|---:|
| service_failure_critical | 8.0 | 0.88 | 2 | 8 / 0 / 0 |
| high_value_slow_delivery_high | 7.0 | 0.82 | 2 | 8 / 2 / 0 |
| ambiguous_medium | 6.0 | 0.72 | 1 | 6 / 3 / 1 |
| low_risk_soft_engagement | 6.5 | 0.78 | 1 | 6 / 2 / 2 |
| high_value_review_concern_high | 4.5 | 0.92 | 2 | 5 / 0 / 3 |
| weak_signal_new_customer_medium | 4.0 | 0.95 | 2 | 3 / 1 / 5 |
| **Mean / range** | **6.00** | — | — | **range 4.0 – 8.0** |

The rubric is doing real work — the same emails scored 8.5–9.0 cluster under a permissive rubric. Low scores in the table above flag genuine generator bugs (wrong CTA intent, offer-when-prohibited, tone-vs-label disagreement) that are then fed back as system-prompt revisions.

---

## Quick Start

### Prerequisites
- Python 3.11+
- Docker (for local Postgres)
- The Olist dataset zip at `data/raw_data.zip` (free from Kaggle, ~45 MB)

### Run the data pipeline

```bash
pip install -e .                               # backend package + db deps
docker compose up -d                           # local Postgres 16

unzip data/raw_data.zip -d data/raw            # extract the 9 Olist CSVs

PYTHONPATH=src python -m backend.db.loader.raw_loader         # CSVs -> raw schema
PYTHONPATH=src python -m backend.db.simulation.repeat_orders  # synthetic repeat orders
dbt build --project-dir src/transform --profiles-dir src/transform   # silver views + gold + tests
```

Explore the orchestration graph with `cd src/orchestration && dagster dev`.

### Dashboard

A React + Tailwind dashboard over dbt, Postgres, and MLflow — with a button to
run batch scoring with the champion model:

```bash
PYTHONPATH=src uvicorn backend.api.app:app --port 8000   # FastAPI backend
cd src/dashboard && npm install && npm run dev           # UI at localhost:5173
```

### Tests

Unit tests for the ML and API logic (no database required — the gold table is
stubbed and the run log is redirected to a temp file):

```bash
pip install -e ".[dev]"   # installs pytest
pytest                    # runs tests/
```

## Evaluation Framework

Two complementary scorers run against every generated email; their disagreement is the signal.

### Tier 1 — DistilBERT inline classifier

A fine-tuned DistilBERT model (`src/backend/eval/distilbert/`) under PyTorch + Hugging Face, trained on a Claude-generated corpus of `{email, score}` pairs and registered in MLflow alongside the churn model. Runs in tens of milliseconds per email; cheap enough to score every send.

### Tier 2 — Adversarial LLM-as-judge

`src/ai/grader.py` calls `claude-haiku-4-5` with a structured-output schema and an explicitly adversarial system prompt. Key design choices:

- **Forced clause enumeration** — every distinct clause in the test case's `success_criteria` produces one entry in `clauses_evaluated` with a verdict enum (`met` / `partially_met` / `not_met` / `not_assessable`) and a quoted evidence string. No vague "the tone feels off" reasoning is allowed.
- **Mandatory weakness list** — judge must surface ≥2 specific weaknesses per email, even strong ones. If it can't find two, it's reading too charitably.
- **Calibration anchors** — default score 6, competent baseline 7, 10 reserved for "essentially never awarded". Pushes the prior away from sycophantic 9s.
- **Hard caps** — any `MUST` violated caps at 6; any `must NOT` (e.g., the "we miss you" trope) caps at 3; fabricated facts cap at 5; schema failures cap at 1.
- **Tool-call provenance** — the generator's tool-call log (`{name, input, output}` per call) is forwarded into the grade payload, so the judge can verify cited numbers against real tool outputs before applying the fabrication cap.

### Disagreement analysis

DistilBERT and the Claude judge are designed to be directly comparable. Where they disagree, the test case becomes a candidate for prompt iteration (generator side) or rubric tightening (judge side). The adversarial rubric explicitly exists to widen the score range and surface failure modes a permissive rubric would hide.

---

## Engineering Decisions

A few choices worth justifying:

### Why a custom churn definition over a pre-labeled dataset?
Pre-labeled churn datasets (Telco, etc.) are tutorial-tier and over-used. Defining churn from raw transactional data demonstrates the actual problem-framing skill that production ML engineers need. Full reasoning in [`docs/data_definition.md`](docs/data_definition.md).

### Why XGBoost over a neural network for churn prediction?
Tabular classification with ~85K rows is XGBoost's home turf. A neural network here would underperform on accuracy *and* take longer to train. Using deep learning for this would signal "I don't know when to use what."

### Why DistilBERT for eval, not GPT-4 / Claude every time?
Cost and latency. DistilBERT runs in 22ms locally for ~$0 per inference. Claude as a judge costs $0.003 per email and adds 1.5s latency. The two-tier pattern uses each model where it's strongest.

### Why tool-augmented generation instead of stuffing the prompt?
Pre-loading every customer's order history, reviews, and category baselines into the prompt would 10× the input-token cost and most of it would go unread. Instead, the generator calls read-only DB tools (`get_customer_delivery_stats`, `get_customer_recent_orders`, `get_category_baseline`, `get_customer_review_history`) only when a SHAP risk driver warrants concrete grounding. The system prompt sets hard restraint rules (zero tool calls for low-risk or weak-signal cases) so the model doesn't fire-hose the DB unnecessarily.

### Why an adversarial rubric for the LLM judge?
The first pass clustered every email at 8.5–9.0 — useless as a feedback signal. Rewriting the rubric with explicit calibration anchors (default 6, competent baseline 7, 10 essentially never awarded), forced per-clause enumeration with an enum-typed verdict, and mandatory weakness enumeration moved the distribution to mean 6.00 with a 4.0–8.0 range — and started catching real generator bugs (wrong CTA intent on a high-LTV customer, offer-when-prohibited on a weak-signal customer, tone-vs-label disagreement). Forwarding the generator's tool-call log into the grade payload prevents the judge from flagging real DB-sourced numbers as fabrications.

### Why AWS App Runner over Kubernetes?
This is a single-service application. Kubernetes here would be over-engineering, and senior reviewers correctly identify that as resume padding. App Runner handles the actual production concerns (auto-scaling, HTTPS, deployments) without the operational tax.

### Why Pydantic schemas at every boundary?
The ML→LLM handoff is the architectural core of this project. Pydantic enforces type safety at that boundary, which means the contract is self-documenting and validation happens automatically. It also makes structured outputs from the LLM's tool use API directly mappable to typed Python objects.

### Why MLflow over Weights & Biases?
Both work. MLflow appears in more job postings and is open-source/self-hostable, which is the better signal for production ML engineering vs SaaS-dependent workflows.

### Why a Postgres medallion pipeline over file-based ETL?
Holding the raw and transformed data in one queryable database makes the pipeline reproducible and inspectable end to end. dbt owns the silver/gold transformations — tests and lineage for free. See [`docs/adr/0001`](docs/adr/0001-postgres-medallion-architecture.md).

### Why synthetic data augmentation?
Olist has almost no repeat customers (~3%), so an honest churn label is ~98% positive and unlearnable. A signal-driven simulation adds repeat orders whose timing depends on real first-order experience, making churn a genuine prediction task. The dataset is presented as Olist-plus-simulation, never as raw Olist. See [`docs/adr/0004`](docs/adr/0004-synthetic-repeat-order-augmentation.md).

---

## Project Structure

```
retention-flow/
├── src/
│   ├── ai/                 # Claude email generation + LLM-as-judge eval
│   │   ├── claude.py           # Anthropic client, run_conversation, generate_email
│   │   ├── tools.py            # Tool dispatcher (TOOL_FUNCTIONS registry)
│   │   ├── tools_schema.py     # Tool input schemas + structured-output configs
│   │   ├── db_tools.py         # Read-only DB tools the generator can call
│   │   ├── grader.py           # Adversarial LLM-as-judge (tier 2 eval)
│   │   ├── prompts/            # Cached system prompts + test cases w/ success criteria
│   │   └── test/               # Test driver + real-customer SHAP picker
│   ├── backend/
│   │   ├── db/             # database access — engine + config + models + migrations
│   │   │   ├── loader/         # one-time CSV -> raw schema migration
│   │   │   └── simulation/     # signal-driven synthetic repeat-order generator
│   │   ├── ml/             # XGBoost churn model — data prep + training
│   │   ├── api/            # FastAPI dashboard backend + batch scoring (SSE)
│   │   └── eval/distilbert/    # tier-1 email-quality classifier (PyTorch + HF)
│   ├── transform/          # dbt project
│   │   └── models/
│   │       ├── staging/        # stg_* views (silver) — raw + synthetic union
│   │       ├── intermediate/   # int_customer_orders (wide order table)
│   │       └── marts/          # customer_features (gold table)
│   ├── orchestration/      # Dagster project — dbt assets + nightly schedule
│   └── dashboard/          # React + Tailwind + TypeScript dashboard (Vite)
├── notebooks/              # EDA + experimentation (churn_xgboost.ipynb)
├── tests/                  # pytest suite — ML + API unit tests
├── logs/mlruns/            # local MLflow tracking store (gitignored)
├── data/raw/               # Olist CSVs (gitignored)
├── docs/adr/               # Architecture decision records
├── CONTEXT.md              # Domain glossary
├── docker-compose.yml      # Local Postgres
└── pyproject.toml
```

---

## Documentation

Decision records and the domain glossary:

- [`CONTEXT.md`](CONTEXT.md) — Domain glossary: medallion layers, churn label, split
- [`docs/adr/0001-postgres-medallion-architecture.md`](docs/adr/0001-postgres-medallion-architecture.md) — Postgres medallion architecture with dbt and Dagster
- [`docs/adr/0002-future-window-churn-label.md`](docs/adr/0002-future-window-churn-label.md) — Why churn is a forward-looking label
- [`docs/adr/0003-dagster-for-orchestration.md`](docs/adr/0003-dagster-for-orchestration.md) — Dagster over plain cron
- [`docs/adr/0004-synthetic-repeat-order-augmentation.md`](docs/adr/0004-synthetic-repeat-order-augmentation.md) — Signal-driven synthetic repeat orders

---

## Roadmap

Done in `src/ai/`:

- [x] Tool-augmented Claude email generation with structured output
- [x] Adversarial LLM-as-judge with calibrated rubric, per-clause enumeration, hard caps
- [x] Real-customer test cases across all four risk tiers (`build_real_test_cases.py`)
- [x] Tool-call provenance forwarded into the grade payload

Open work:

- [ ] **Wire DistilBERT inline scorer into the email-gen pipeline** (model exists in `eval/distilbert/`, not yet called per-email)
- [ ] **Disagreement analysis dashboard panel** — surface emails where DistilBERT and Claude judge land far apart
- [ ] **Online feedback loop**: capture whether emailed customers stayed, retrain on outcomes
- [ ] **A/B testing framework**: multiple prompt strategies per customer segment with statistical rigor
- [ ] **Prompt versioning**: registry for prompt variants with rollback support
- [ ] **Cost-tier routing**: smaller models for low-risk customers, larger for high-risk
- [ ] **Per-prediction SHAP on demand** for non-critical risk tiers (currently only top-200 customers have persisted SHAP)
- [ ] **Async batch generation** — `AsyncAnthropic` or Message Batches API for the nightly run over the top-N at-risk customers

---

## Contributing

This is primarily a personal study project, but issues and discussion are welcome. If you spot a bug or have a suggestion, please open an issue. For substantial changes, please open an issue first to discuss what you'd like to change.

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for development workflow.

---

## License

[MIT](LICENSE)

---

## Acknowledgments

- Olist Brazilian E-commerce dataset by Olist via Kaggle
- SHAP library by Scott Lundberg
- The applied ML community for documenting production patterns publicly

---

<sub>Built by [@jhatch03](https://github.com/jhatch03). If this project was useful to you, star the repo or [reach out](mailto:jjhatch03@gmail.com) — always interested in talking applied AI engineering.</sub>
