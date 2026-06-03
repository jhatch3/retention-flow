"""Shared AI/model configuration.

One home for the model id so it can't drift across the generator, the judge,
the synchronous helpers, and the dashboard's display fallback.
"""

# Default Anthropic model for generation + judging.
DEFAULT_MODEL = "claude-haiku-4-5"
