"""Load and tokenize the email-quality corpus for fine-tuning.

The training data is a static, Claude-generated JSONL file — one
``{"email": ..., "score": ...}`` record per line, ``score`` an integer 1-5.
This module reads it, schema-validates each record, tokenizes the email text
with the DistilBERT tokenizer, and produces a deterministic, score-stratified
train/validation/test split. The corpus carries no split column — the split
is computed here at load time.

Scores (1-5) are mapped to zero-based class labels (0-4) for the
sequence-classification head; see ``score_to_label`` / ``label_to_score``.

``datasets`` is imported lazily so the pure functions here (and their tests)
do not require the deep-learning stack.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from .model import MAX_SEQ_LENGTH, build_tokenizer

# The committed, Claude-generated training corpus (JSONL).
DATASET_PATH = Path(__file__).resolve().parent / "dataset" / "email_quality.jsonl"

# Quality-grade label space — matches the model's softmax(5) head.
MIN_SCORE = 1
MAX_SCORE = 5

# Deterministic split (stratified by score) computed at load time.
SPLIT_FRACTIONS = {"train": 0.70, "validation": 0.15, "test": 0.15}
SPLIT_SEED = 42


def score_to_label(score: int) -> int:
    """Map a 1-5 quality score to a 0-based classification label."""
    return score - MIN_SCORE


def label_to_score(label: int) -> int:
    """Map a 0-based classification label back to a 1-5 quality score."""
    return label + MIN_SCORE


def load_records(path: Path = DATASET_PATH) -> list[dict]:
    """Read and schema-validate the JSONL corpus.

    Each non-blank line must be a JSON object ``{"email": str, "score": int}``
    with ``score`` in ``[MIN_SCORE, MAX_SCORE]``. Raises ``FileNotFoundError``
    if the corpus is missing and ``ValueError`` on the first malformed record
    or an empty corpus.
    """
    if not path.exists():
        raise FileNotFoundError(f"email-quality corpus not found: {path}")

    records: list[dict] = []
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path.name} line {lineno}: invalid JSON ({exc})") from exc

        email, score = row.get("email"), row.get("score")
        if not isinstance(email, str) or not email.strip():
            raise ValueError(
                f"{path.name} line {lineno}: 'email' must be a non-empty string"
            )
        # bool is an int subclass — reject it explicitly.
        if not isinstance(score, int) or isinstance(score, bool):
            raise ValueError(f"{path.name} line {lineno}: 'score' must be an integer")
        if not MIN_SCORE <= score <= MAX_SCORE:
            raise ValueError(
                f"{path.name} line {lineno}: 'score' {score} outside "
                f"[{MIN_SCORE}, {MAX_SCORE}]"
            )
        records.append({"email": email, "score": score})

    if not records:
        raise ValueError(f"{path.name}: corpus is empty")
    return records


def split_records(records: list[dict]) -> dict[str, list[dict]]:
    """Deterministic, score-stratified train/validation/test split.

    Each score bucket is shuffled with a fixed seed and partitioned by
    ``SPLIT_FRACTIONS``, so every split carries the same grade distribution and
    the assignment is reproducible across runs.
    """
    rng = random.Random(SPLIT_SEED)
    buckets: dict[int, list[dict]] = {}
    for rec in records:
        buckets.setdefault(rec["score"], []).append(rec)

    splits: dict[str, list[dict]] = {"train": [], "validation": [], "test": []}
    for score in sorted(buckets):
        bucket = buckets[score][:]
        rng.shuffle(bucket)
        n = len(bucket)
        n_train = int(n * SPLIT_FRACTIONS["train"])
        n_val = int(n * SPLIT_FRACTIONS["validation"])
        splits["train"].extend(bucket[:n_train])
        splits["validation"].extend(bucket[n_train : n_train + n_val])
        splits["test"].extend(bucket[n_train + n_val :])

    for name in splits:
        rng.shuffle(splits[name])
    return splits


def tokenize(records: list[dict], tokenizer):
    """Tokenize email text into a Hugging Face ``Dataset`` with a ``labels`` column.

    Padding is left to the ``Trainer``'s data collator; only truncation is
    applied here.
    """
    from datasets import Dataset

    encodings = tokenizer(
        [r["email"] for r in records],
        truncation=True,
        max_length=MAX_SEQ_LENGTH,
    )
    encodings["labels"] = [score_to_label(r["score"]) for r in records]
    return Dataset.from_dict(encodings)


def load_dataset():
    """Full pipeline: load -> validate -> split -> tokenize.

    Returns a ``datasets.DatasetDict`` with ``train`` / ``validation`` / ``test``
    splits, each tokenized and carrying a 0-based ``labels`` column, ready for
    the Hugging Face ``Trainer``.
    """
    from datasets import DatasetDict

    tokenizer = build_tokenizer()
    splits = split_records(load_records())
    return DatasetDict(
        {name: tokenize(recs, tokenizer) for name, recs in splits.items()}
    )
