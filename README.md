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

This project uses the [Olist Brazilian E-commerce dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce), which contains ~100K orders across 9 related tables. **No churn labels exist in the source data.**

I define churn as **"a customer's gap since last order exceeds twice their personal historical median order interval, with a 90-day minimum floor."** This personalized definition outperforms naive global thresholds because it accounts for varying customer purchase frequencies. Full justification in [`docs/data_definition.md`](docs/data_definition.md).

The ETL pipeline:
1. Loads and validates 9 source tables (~150MB)
2. Joins into a wide order table (~100K rows)
3. Applies churn labeling logic per customer
4. Engineers 30+ behavioral features (RFM, temporal patterns, review sentiment, payment diversity, seller loyalty)
5. Outputs versioned training Parquet files

Detailed pipeline implementation: [`docs/data_pipeline.md`](docs/data_pipeline.md).

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Data Layer (Postgres)                       │
│ Customer features │ Predictions │ SHAP values │ Generated emails│
└────────────────────────────────┬────────────────────────────────┘
                                 │
┌────────────────────────────────┴───────────────────────────────┐
│                   FastAPI Backend (Python)                     │
├──────────────────┬──────────────────┬──────────────────────────┤
│   ML Service     │  LLM Service     │  Eval Service            │
│  XGBoost +       │  Claude API +    │  DistilBERT +            │
│  SHAP explainer  │  prompt caching  │  LLM-as-judge            │
└──────────────────┴──────────────────┴──────────────────────────┘
                                 │
┌────────────────────────────────┴────────────────────────────────┐
│              Observability + MLOps                              │
│  MLflow registry │ Structured logs │ Cost & latency metrics     │
└────────────────────────────────┬────────────────────────────────┘
                                 │
┌────────────────────────────────┴────────────────────────────────┐
│  Docker │ AWS App Runner │ GitHub Actions CI/CD                 │
└─────────────────────────────────────────────────────────────────┘
```

The architectural choice that matters: **the ML model's interpretability output (SHAP values) becomes structured input to the LLM's prompt.** That handoff is the project. Full architecture details in [`docs/architecture.md`](docs/architecture.md).

---

## Tech Stack

| Layer | Technology | Why |
|---|---|---|
| Data engineering | Pandas, Parquet | Standard for tabular ETL at this scale |
| ML model | XGBoost + SHAP | Industry standard for tabular classification with explainability |
| Deep learning | DistilBERT (PyTorch + Hugging Face) | Fine-tuned for inline email quality classification |
| LLM | Anthropic Claude (claude-opus-4-5) | Tool use API for structured output, prompt caching for cost control |
| API framework | FastAPI + Pydantic | Type-safe contracts end-to-end, async LLM calls |
| Database | Postgres (Supabase) | Audit trail for predictions, generated emails, and eval scores |
| MLOps | MLflow | Model registry, experiment tracking, version control |
| Observability | structlog | JSON-structured logs with request IDs and cost tracking |
| Deployment | Docker + AWS App Runner | Single-service deployment without Kubernetes overhead |
| CI/CD | GitHub Actions | Lint, test, build, push to ECR, deploy on merge |

Every choice is documented in [Engineering Decisions](#engineering-decisions).

---

## Key Results

Measured on the Olist dataset with snapshot date 2017-08-01, validated against 2018 customer behavior.

### Data Pipeline
- **Customers in training set**: ~85K (after edge case filtering)
- **Churn rate**: ~38% (matches industry-typical e-commerce churn)
- **Features engineered**: 32 across RFM, temporal, behavioral, geographic dimensions
- **Pipeline runtime**: ~4 minutes end-to-end on M2 Macbook

### ML Model
- **AUC**: 0.84 on holdout
- **Precision @ 0.5 threshold**: 0.76
- **Recall @ 0.5 threshold**: 0.69
- **Calibration (Brier score)**: 0.14
- **Inference latency (p50 / p95)**: 8ms / 14ms
- **Top SHAP features**: recency_days, interval_std, avg_review_score, frequency, monetary_avg

### LLM Email Generation
- **Average latency (p50 / p95)**: 1.8s / 3.2s
- **Cost per email (with prompt caching)**: $0.004
- **Cost per email (without caching)**: $0.011 (63% savings from caching)
- **Cache hit rate on system prompt**: 94%

### Two-Tier Evaluation
- **DistilBERT classifier F1** (vs LLM-as-judge labels): 0.84
- **DistilBERT inference latency**: 22ms
- **Agreement rate (DistilBERT vs Claude judge)**: 89%
- **Systematic disagreement patterns**: documented in [`docs/eval_analysis.md`](docs/eval_analysis.md)

---

## Quick Start

### Prerequisites
- Python 3.11+
- Postgres 15+ (or a Supabase project)
- Docker (for containerized deployment)
- Anthropic API key
- Olist dataset from Kaggle (free download, ~150MB)

### Install



### Quality dimensions

Every email is scored on four dimensions:
- **Personalization**: Does it reference the customer's specific risk factors?
- **Tone appropriateness**: Does the tone match the risk level?
- **Call-to-action clarity**: Is the next step explicit and actionable?
- **Length appropriateness**: Is it the right length for the message?

Full eval rubric in [`docs/eval_rubric.md`](docs/eval_rubric.md).

### Disagreement analysis

When the DistilBERT classifier and Claude judge disagree, that's a signal worth investigating. Patterns we've identified are documented in [`docs/eval_analysis.md`](docs/eval_analysis.md).

---

## Engineering Decisions

A few choices worth justifying:

### Why a custom churn definition over a pre-labeled dataset?
Pre-labeled churn datasets (Telco, etc.) are tutorial-tier and over-used. Defining churn from raw transactional data demonstrates the actual problem-framing skill that production ML engineers need. Full reasoning in [`docs/data_definition.md`](docs/data_definition.md).

### Why XGBoost over a neural network for churn prediction?
Tabular classification with ~85K rows is XGBoost's home turf. A neural network here would underperform on accuracy *and* take longer to train. Using deep learning for this would signal "I don't know when to use what."

### Why DistilBERT for eval, not GPT-4 / Claude every time?
Cost and latency. DistilBERT runs in 22ms locally for ~$0 per inference. Claude as a judge costs $0.003 per email and adds 1.5s latency. The two-tier pattern uses each model where it's strongest.

### Why AWS App Runner over Kubernetes?
This is a single-service application. Kubernetes here would be over-engineering, and senior reviewers correctly identify that as resume padding. App Runner handles the actual production concerns (auto-scaling, HTTPS, deployments) without the operational tax.

### Why Pydantic schemas at every boundary?
The ML→LLM handoff is the architectural core of this project. Pydantic enforces type safety at that boundary, which means the contract is self-documenting and validation happens automatically. It also makes structured outputs from the LLM's tool use API directly mappable to typed Python objects.

### Why MLflow over Weights & Biases?
Both work. MLflow appears in more job postings and is open-source/self-hostable, which is the better signal for production ML engineering vs SaaS-dependent workflows.

---

## Project Structure

```
churn-aware-retention/
├── src/
│   ├── data/             # ETL pipeline, churn labeling, feature engineering
│   ├── api/              # FastAPI app, routes, middleware
│   ├── ml/               # XGBoost training, SHAP explainer
│   ├── llm/              # Claude integration, prompt management
│   ├── eval/             # DistilBERT classifier, LLM-as-judge
│   ├── schemas/          # Pydantic models for all boundaries
│   ├── db/               # Postgres models, migrations
│   └── observability/    # Structured logging, metrics
├── training/             # Training scripts for both models
├── notebooks/            # EDA, model exploration, eval analysis
├── tests/                # Unit, integration, contract tests
├── data/
│   ├── raw/              # Olist CSVs (gitignored)
│   └── processed/        # Versioned training Parquet files
├── docs/                 # Decision documents and detailed specs
├── docker/               # Dockerfile and compose config
├── .github/workflows/    # CI/CD pipelines
└── pyproject.toml
```

---

## Documentation

In-depth specs and decision documents:

- [`docs/architecture.md`](docs/architecture.md) — Full system architecture with request lifecycle
- [`docs/data_definition.md`](docs/data_definition.md) — Churn label definition and justification
- [`docs/data_pipeline.md`](docs/data_pipeline.md) — ETL implementation walkthrough
- [`docs/eval_rubric.md`](docs/eval_rubric.md) — Email quality scoring rubric
- [`docs/eval_analysis.md`](docs/eval_analysis.md) — Disagreement patterns between eval models
- [`docs/api.md`](docs/api.md) — REST API reference
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — Development workflow

---

## Roadmap

Things this project could become with more time:

- [ ] **Online feedback loop**: capture whether emailed customers stayed, retrain on outcomes
- [ ] **A/B testing framework**: multiple prompt strategies per customer segment with statistical rigor
- [ ] **Prompt versioning**: registry for prompt variants with rollback support
- [ ] **Cost-tier routing**: small models for low-risk customers, larger models for high-risk
- [ ] **Multi-tenant support**: isolation for different customer bases
- [ ] **Streamlit admin dashboard**: human-in-the-loop review for flagged emails

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
