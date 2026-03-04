# RetentionFlow - Inprogress 
Production-Grade Customer Churn Prediction Platform  
Databricks • Delta Lake • TensorFlow • MLflow • Keras • Dagster • Power BI

---

# Overview

RetentionFlow is a production-grade **customer churn prediction platform** designed to help companies identify at-risk customers before they leave. The system ingests customer activity, billing, support, and engagement data into a **Databricks Lakehouse architecture**, generates predictive features, and trains machine learning models to estimate churn probability.

Using **Delta Lake** for reliable data pipelines and **MLflow** for experiment tracking and model lifecycle management, RetentionFlow provides scalable churn predictions that can be consumed by dashboards, APIs, and downstream applications.

Predictions and insights are surfaced through **Power BI dashboards** and **REST APIs**, enabling teams such as customer success, marketing, and product analytics to take proactive retention actions.

**Dagster** is used as the orchestration layer to manage data pipelines, training workflows, and scheduled batch scoring jobs.

This repository will contain the full pipeline for building and deploying the churn prediction system.

---

# Architecture

The platform follows a modern **Lakehouse + MLOps architecture**.

Data is organized using a **Delta Lake medallion architecture**:

Bronze → Silver → Gold

- **Bronze:** Raw ingested customer events  
- **Silver:** Cleaned and standardized customer records  
- **Gold:** Feature tables and churn prediction outputs  

Machine learning models are trained using **TensorFlow**, tracked and versioned using **MLflow**, and deployed for scoring through batch pipelines and APIs.

Dagster orchestrates the entire workflow, including:

- data ingestion
- feature generation
- model training
- batch scoring
- monitoring jobs

---

# Data Flow


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
(real-time churn scoring for apps)
```
---

# Tech Stack

## Data Platform

- Databricks
- Apache Spark (PySpark)
- Delta Lake
- Unity Catalog (data governance)

## Orchestration

- Dagster
- Scheduled pipelines
- Dependency-aware workflow execution

## Machine Learning

- TensorFlow / Keras
- MLflow
- Scikit-learn (feature utilities and evaluation)

## Data Serving

- FastAPI
- REST APIs
- Power BI dashboards

## Infrastructure

- Docker
- Python
- GitHub

---

# Key Features (Planned)

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

# Example Output

Example churn prediction record:
