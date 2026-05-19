"""Fine-tune DistilBERT on the email-quality corpus and register it.

Mirrors the churn model's MLflow workflow (see ``backend.ml.train``): fine-tune
with the Hugging Face ``Trainer``, evaluate on the held-out test split, log
params and metrics, and register the model so ``predict`` can pull the
champion. The local MLflow store is ``logs/mlruns/``, shared with the churn
model.

    python -m backend.eval.distilbert.train

The deep-learning stack (torch / transformers / datasets / mlflow) is imported
lazily inside ``train_and_log`` — importing this module stays cheap.
"""

from __future__ import annotations

import argparse
import tempfile

from .data import load_dataset
from .model import (
    CHAMPION_ALIAS,
    MLFLOW_URI,
    MODEL_NAME,
    NUM_LABELS,
    REGISTERED_MODEL,
    build_model,
    build_tokenizer,
)

EXPERIMENT = "distilbert-email-quality"
RUN_NAME = "distilbert-v1"

# Fine-tuning hyperparameters.
PARAMS: dict = dict(
    learning_rate=2e-5,
    per_device_train_batch_size=16,
    per_device_eval_batch_size=32,
    num_train_epochs=3,
    weight_decay=0.01,
)


def _compute_metrics(eval_pred):
    """Accuracy, macro-F1, and mean absolute grade error for the ``Trainer``."""
    import numpy as np
    from sklearn.metrics import accuracy_score, f1_score

    logits, labels = eval_pred
    preds = np.asarray(logits).argmax(axis=-1)
    labels = np.asarray(labels)
    return {
        "accuracy": float(accuracy_score(labels, preds)),
        "f1_macro": float(f1_score(labels, preds, average="macro")),
        # grades are ordinal — average distance, in grade points, when wrong
        "mae_grades": float(np.abs(preds - labels).mean()),
    }


def train_and_log(run_tags: dict[str, str] | None = None) -> dict:
    """Fine-tune, evaluate on the test split, log to MLflow, and register.

    ``run_tags`` are attached to the MLflow run — the Dagster asset can pass its
    run id here, mirroring the churn model so the two systems cross-reference.
    """
    import mlflow
    import mlflow.transformers
    from mlflow.tracking import MlflowClient
    from transformers import (
        DataCollatorWithPadding,
        Trainer,
        TrainingArguments,
        pipeline,
    )

    dataset = load_dataset()
    tokenizer = build_tokenizer()
    model = build_model()

    mlflow.set_tracking_uri(MLFLOW_URI)
    mlflow.set_experiment(EXPERIMENT)

    with mlflow.start_run(run_name=RUN_NAME) as run:
        if run_tags:
            mlflow.set_tags(run_tags)

        with tempfile.TemporaryDirectory() as tmp:
            args = TrainingArguments(
                output_dir=tmp,
                eval_strategy="epoch",
                save_strategy="no",
                logging_strategy="epoch",
                report_to=[],  # manual MLflow logging — no Trainer integration
                **PARAMS,
            )
            trainer = Trainer(
                model=model,
                args=args,
                train_dataset=dataset["train"],
                eval_dataset=dataset["validation"],
                data_collator=DataCollatorWithPadding(tokenizer),
                compute_metrics=_compute_metrics,
            )
            trainer.train()

            # test is held out from training and from per-epoch evaluation.
            test_metrics = trainer.evaluate(dataset["test"], metric_key_prefix="test")
            val_metrics = trainer.evaluate(
                dataset["validation"], metric_key_prefix="validation"
            )

        mlflow.log_params(PARAMS)
        mlflow.log_param("base_model", MODEL_NAME)
        mlflow.log_param("num_labels", NUM_LABELS)
        mlflow.log_param("n_train", dataset["train"].num_rows)
        mlflow.log_metrics({**test_metrics, **val_metrics})

        # Log the fine-tuned model as a text-classification pipeline so
        # predict.load_champion() gets an inference-ready pipeline back.
        # pip_requirements is passed explicitly: MLflow's auto-inference for the
        # transformers flavor probes torchvision, which a text model never needs.
        pipe = pipeline("text-classification", model=model, tokenizer=tokenizer)
        logged = mlflow.transformers.log_model(
            transformers_model=pipe,
            name="model",
            pip_requirements=["torch", "transformers"],
        )
        run_id = run.info.run_id

    # Register the model and move the champion alias to the new version.
    version = mlflow.register_model(logged.model_uri, REGISTERED_MODEL)
    MlflowClient().set_registered_model_alias(
        REGISTERED_MODEL, CHAMPION_ALIAS, version.version
    )

    return {
        "run_id": run_id,
        "model_name": REGISTERED_MODEL,
        "model_version": version.version,
        "test": test_metrics,
        "validation": val_metrics,
    }


def main() -> int:
    argparse.ArgumentParser(
        description="Fine-tune the DistilBERT email-quality classifier."
    ).parse_args()
    out = train_and_log()

    print(f"MLflow run: {out['run_id']}  (tracking: {MLFLOW_URI})")
    print(
        f"Registered: {out['model_name']} v{out['model_version']} "
        f"-> @{CHAMPION_ALIAS}"
    )
    for split in ("validation", "test"):
        m = out[split]
        print(
            f"  {split:11} "
            f"accuracy={m[f'{split}_accuracy']:.3f}  "
            f"f1_macro={m[f'{split}_f1_macro']:.3f}  "
            f"mae_grades={m[f'{split}_mae_grades']:.3f}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
