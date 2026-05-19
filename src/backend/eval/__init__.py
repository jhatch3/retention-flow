"""Two-tier email-quality evaluation.

Generated retention emails are scored before they go out. Tier 1 is a
fine-tuned DistilBERT classifier (``distilbert/``) — fast and local. Tier 2,
an LLM-as-judge, lands later as ``judge.py``. Both write a row to
``serving.eval_scores`` so their grades can be compared.
"""
