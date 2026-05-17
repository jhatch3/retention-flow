"""FastAPI backend for the RetentionFlow dashboard.

Unifies three sources behind one JSON API: dbt run artifacts, the Postgres
warehouse, and the MLflow registry — plus a batch-scoring endpoint.
"""
