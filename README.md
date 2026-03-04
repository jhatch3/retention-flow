# RetentionFlow
Production-Grade Customer Churn Prediction Platform  
Databricks • Delta Lake • TensorFlow • MLflow • Dagster • Power BI

---

## Overview

RetentionFlow is a production-grade **customer churn prediction platform** designed to help organizations identify at-risk customers before they leave. The system ingests customer activity, billing, support, and engagement data into a **Databricks Lakehouse architecture**, generates predictive features, and trains machine learning models to estimate churn probability.

Using **Delta Lake** for reliable data pipelines and **MLflow** for experiment tracking and model lifecycle management, RetentionFlow provides scalable churn predictions that can be consumed by dashboards, APIs, and downstream applications.

Predictions and insights are surfaced through **Power BI dashboards** and **REST APIs**, enabling teams such as customer success, marketing, and product analytics to take proactive retention actions.

**Dagster** is used as the orchestration layer to coordinate ingestion pipelines, feature engineering workflows, model training, scoring jobs, and monitoring tasks.

This repository will contain the full pipeline for building and deploying the churn prediction system.

---

## Architecture

RetentionFlow follows a modern **Lakehouse + MLOps architecture** built for reproducibility, scalability, and operational deployment.

Data is organized using a **Delta Lake medallion architecture**:

**Bronze → Silver → Gold**

- **Bronze:** Raw ingested customer events  
- **Silver:** Cleaned and standardized customer records  
- **Gold:** Curated feature tables and churn prediction outputs  

Machine learning models are trained using **TensorFlow**, tracked and versioned using **MLflow**, and deployed for scoring through batch pipelines and APIs.

Dagster orchestrates the full workflow across data pipelines, training jobs, scoring pipelines, and monitoring tasks.

---

## Data Flow

``` 
Data Sources
(billing, product usage, CRM, support, marketing events)
│
▼
Dagster Orchestration
(schedule + dependency management)
│
▼
Databricks Ingestion
(Spark / Auto Loader / batch pipelines)
│
▼
Delta Lake Medallion Architecture
Bronze → Silver → Gold
│
▼
Feature Engineering (Spark)
customer_features_daily
│
▼
Model Training (TensorFlow)
│
▼
MLflow Tracking + Model Registry
(Staging → Production)
│
▼
Batch Scoring Pipeline
│
▼
Delta Tables
gold.predictions_daily
│
▼
Power BI Dashboards
(Customer risk monitoring)
│
▼
REST APIs
(real-time churn scoring for applications)
```


---

## Tech Stack

### Data Platform
- Databricks
- Apache Spark (PySpark)
- Delta Lake
- Unity Catalog (data governance and lineage)

### Orchestration
- Dagster
- Scheduled pipelines
- Dependency-aware workflow orchestration

### Machine Learning
- TensorFlow / Keras
- MLflow
- Scikit-learn (feature utilities and evaluation)

### Data Serving
- FastAPI
- REST APIs
- Power BI dashboards

### Infrastructure
- Docker
- Python
- GitHub

---

## MLOps Design

RetentionFlow is designed following **production-grade MLOps practices**.

### Reproducible Pipelines
- Delta Lake provides **ACID transactions, time travel, and schema enforcement**
- Medallion architecture enables **traceable lineage from raw ingestion to predictions**

### Orchestrated Workflows
- Dagster manages dependencies between ingestion, features, training, and scoring jobs
- Pipelines are scheduled and retryable with clear observability

### Experiment Tracking and Model Lifecycle
- MLflow tracks:
  - parameters, datasets, metrics, and artifacts
- Models are promoted via the **MLflow Model Registry**:
  - **Staging → Production**

### CI/CD and Environment Promotion
- Promotion flow:
  - **Dev → Staging → Production**
- Automated checks validate:
  - schema contracts, pipeline correctness, model training, scoring, and API endpoints

### Data Quality and Validation
Pipelines enforce:
- schema validation
- null and duplicate detection
- freshness checks
- anomaly detection

Runs fail early when quality thresholds are violated.

### Point-in-Time Correct Features
Feature generation enforces **point-in-time correctness** to prevent label leakage during training and evaluation.

### Monitoring and Drift Detection
Monitoring covers:
- feature distribution drift
- model performance degradation
- prediction volume anomalies
- data freshness

Alerts trigger when thresholds are exceeded.

### Reliable Model Serving
Predictions are delivered through:
- **batch scoring pipelines**
- **versioned REST APIs**

APIs include:
- input validation
- versioned models
- rollback via MLflow model versions

---

## Key Features (Planned)

- Lakehouse Medallion Data Architecture  
- Scalable Feature Engineering with Spark  
- TensorFlow Churn Prediction Model  
- MLflow Experiment Tracking + Model Registry  
- Automated Retraining Pipelines  
- Dagster Pipeline Orchestration  
- Batch Churn Scoring  
- REST API for Real-Time Predictions  
- Power BI Customer Risk Dashboards  
- Model Monitoring and Drift Detection  

---

## Example Output

Example churn prediction record:

```
customer_id: 18423
churn_probability: 0.82
risk_tier: High
```

---

## Repository Status

⚠️ **Project Status: In Progress**

This repository is currently under development.

Planned development phases:

1. Lakehouse data pipeline architecture  
2. Feature engineering framework  
3. TensorFlow churn prediction model  
4. MLflow experiment tracking  
5. Dagster pipeline orchestration  
6. Batch scoring pipelines  
7. Power BI dashboards  
8. API serving layer  

---

## Future Roadmap

- Real-time churn scoring
- Feature store integration
- Automated model retraining
- Experiment comparison dashboards
- Drift detection and model monitoring
- Retention intervention recommendation system

---

## Author

Justin Hatch  
Computer Science — Machine Learning, Data Science, and AI  
University of Oregon

