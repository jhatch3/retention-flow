"""DistilBERT email-quality classifier — tier 1 of the eval stack.

A DistilBERT encoder fine-tuned (PyTorch + Hugging Face) to grade a generated
retention email's overall quality on a 1-5 scale. Built for inline use: it
runs locally in tens of milliseconds, so every email can be scored before the
slower LLM judge is consulted.

Modules
-------
data     load and tokenize the labelled email/score corpus
model    construct / load the DistilBERT sequence classifier
train    fine-tune, evaluate, and register the model in MLflow
predict  score a single email inline
"""
