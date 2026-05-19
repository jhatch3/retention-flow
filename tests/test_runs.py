"""Tests for backend.api.runs — the JSON-backed pipeline run log.

`RUNS_FILE` is monkeypatched onto a temp path so the tests never touch the
real ``data/runs.json``.
"""

import time

import pytest

from backend.api import runs


@pytest.fixture
def runs_file(tmp_path, monkeypatch):
    """Point the run log at an isolated temp file for the duration of a test."""
    path = tmp_path / "runs.json"
    monkeypatch.setattr(runs, "RUNS_FILE", path)
    return path


def test_load_returns_empty_list_when_the_file_is_absent(runs_file):
    assert runs._load() == []


def test_load_returns_empty_list_for_corrupt_json(runs_file):
    runs_file.write_text("{not valid json")
    assert runs._load() == []


def test_record_run_then_read_it_back(runs_file):
    runs.record_run("rebuild", "success", time.perf_counter(), "26 dbt nodes")

    result = runs.recent_runs()
    assert len(result["runs"]) == 1
    record = result["runs"][0]
    assert record["kind"] == "rebuild"
    assert record["status"] == "success"
    assert record["detail"] == "26 dbt nodes"
    assert record["id"].startswith("run-")
    assert record["duration_s"] >= 0


def test_records_are_returned_newest_first(runs_file):
    runs.record_run("rebuild", "success", time.perf_counter(), "first")
    runs.record_run("pipeline", "success", time.perf_counter(), "second")
    details = [r["detail"] for r in runs.recent_runs()["runs"]]
    assert details == ["second", "first"]


def test_the_log_is_capped_at_max_runs(runs_file, monkeypatch):
    monkeypatch.setattr(runs, "MAX_RUNS", 3)
    for i in range(5):
        runs.record_run("rebuild", "success", time.perf_counter(), f"run {i}")

    kept = runs._load()
    assert len(kept) == 3
    assert kept[0]["detail"] == "run 4"  # newest survives the cap


def test_recent_runs_respects_the_limit(runs_file):
    for i in range(5):
        runs.record_run("rebuild", "success", time.perf_counter(), f"run {i}")
    assert len(runs.recent_runs(limit=2)["runs"]) == 2
