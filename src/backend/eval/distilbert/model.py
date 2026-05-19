"""Construct and load the DistilBERT sequence classifier.

A pretrained DistilBERT encoder with a 5-class sequence-classification head —
one class per quality grade. Shared by ``train`` (a fresh model to fine-tune)
and ``predict`` (the fine-tuned model pulled from the MLflow registry).

Hugging Face / MLflow imports are deferred into the functions so this module —
and its constants — can be imported without the deep-learning stack present
(the unit tests rely on that).
"""

from __future__ import annotations

from pathlib import Path

MODEL_NAME = "distilbert-base-uncased"
NUM_LABELS = 5  # quality grades 1-5
MAX_SEQ_LENGTH = 512

# MLflow registry coordinates. The local store is logs/mlruns/, shared with
# the churn model (see backend.ml.train). train.py registers the model here;
# predict.py pulls the champion.
#   .../src/backend/eval/distilbert/model.py -> repo root is parents[4]
MLFLOW_URI = (Path(__file__).resolve().parents[4] / "logs" / "mlruns").as_uri()
REGISTERED_MODEL = "distilbert-email-quality"
CHAMPION_ALIAS = "champion"


def build_tokenizer():
    """Load the DistilBERT tokenizer for ``MODEL_NAME``."""
    from transformers import AutoTokenizer

    return AutoTokenizer.from_pretrained(MODEL_NAME)


def build_model():
    """A fresh ``DistilBertForSequenceClassification`` with ``NUM_LABELS`` heads.

    The encoder is pretrained; the classification head is randomly initialised
    and learned during fine-tuning. ``id2label`` maps each class index to its
    1-5 grade string, so an inference pipeline returns the grade directly.
    """
    from transformers import AutoModelForSequenceClassification

    id2label = {i: str(i + 1) for i in range(NUM_LABELS)}  # 0 -> "1", ... 4 -> "5"
    label2id = {grade: idx for idx, grade in id2label.items()}
    return AutoModelForSequenceClassification.from_pretrained(
        MODEL_NAME,
        num_labels=NUM_LABELS,
        id2label=id2label,
        label2id=label2id,
    )


def load_champion():
    """Load the fine-tuned, registered champion as a text-classification pipeline."""
    import mlflow
    import mlflow.transformers

    mlflow.set_tracking_uri(MLFLOW_URI)
    return mlflow.transformers.load_model(
        f"models:/{REGISTERED_MODEL}@{CHAMPION_ALIAS}"
    )
