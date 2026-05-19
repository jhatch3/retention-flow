"""Tests for backend.eval.distilbert.data — corpus loading and splitting.

These cover the pure data layer only. Importing ``data`` does not pull in
torch / transformers / datasets (those imports are deferred), so the suite
runs without the deep-learning stack installed. The tokenizer, model, and
Trainer are exercised by an actual fine-tuning run, not by unit tests.
"""

import pytest

from backend.eval.distilbert import data


# --- score <-> label mapping ---------------------------------------------

def test_score_label_roundtrip():
    for score in range(data.MIN_SCORE, data.MAX_SCORE + 1):
        assert data.label_to_score(data.score_to_label(score)) == score


def test_score_to_label_is_zero_based():
    assert data.score_to_label(data.MIN_SCORE) == 0
    assert data.score_to_label(data.MAX_SCORE) == data.MAX_SCORE - data.MIN_SCORE


# --- load_records --------------------------------------------------------

def test_load_records_reads_the_committed_corpus():
    records = data.load_records()
    assert len(records) > 0
    for rec in records:
        assert isinstance(rec["email"], str) and rec["email"].strip()
        assert data.MIN_SCORE <= rec["score"] <= data.MAX_SCORE


def test_load_records_rejects_out_of_range_score(tmp_path):
    bad = tmp_path / "bad.jsonl"
    bad.write_text('{"email": "hi", "score": 9}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="outside"):
        data.load_records(bad)


def test_load_records_rejects_malformed_json(tmp_path):
    bad = tmp_path / "bad.jsonl"
    bad.write_text("{not json\n", encoding="utf-8")
    with pytest.raises(ValueError, match="invalid JSON"):
        data.load_records(bad)


def test_load_records_rejects_non_integer_score(tmp_path):
    bad = tmp_path / "bad.jsonl"
    bad.write_text('{"email": "hi", "score": "five"}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="must be an integer"):
        data.load_records(bad)


def test_load_records_rejects_empty_corpus(tmp_path):
    empty = tmp_path / "empty.jsonl"
    empty.write_text("\n   \n", encoding="utf-8")
    with pytest.raises(ValueError, match="empty"):
        data.load_records(empty)


def test_load_records_raises_on_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        data.load_records(tmp_path / "nope.jsonl")


# --- split_records -------------------------------------------------------

def test_split_records_is_deterministic():
    records = data.load_records()
    first = data.split_records(records)
    second = data.split_records(records)
    assert [r["email"] for r in first["train"]] == [
        r["email"] for r in second["train"]
    ]


def test_split_records_partitions_every_record_exactly_once():
    records = data.load_records()
    splits = data.split_records(records)
    assert set(splits) == {"train", "validation", "test"}
    assert sum(len(v) for v in splits.values()) == len(records)


def test_split_records_is_score_stratified():
    """Every score bucket should be represented in the train split."""
    records = data.load_records()
    splits = data.split_records(records)
    assert {r["score"] for r in splits["train"]} == {r["score"] for r in records}
