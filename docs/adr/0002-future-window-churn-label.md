# Future-window churn label

The README defined churn as a customer's gap since their last order exceeding
twice their personal median order interval (90-day floor), evaluated *at* the
snapshot date. That definition is target-leaky: `recency_days` is both a
feature and, by construction, the label — `is_churned ≈ (recency_days >
threshold)`. A model with recency as a feature re-derives the label's own rule
instead of predicting anything.

We redefine churn as a forward-looking label. At the snapshot date, a customer
is churned if they place **no order within the observation horizon** afterwards
(default 180 days). Features are computed only from events on or before the
snapshot date; the label only from the window strictly after it. This keeps
recency a legitimate predictor and makes churn a genuine prediction task.

## Consequences

- The snapshot date must sit far enough before the end of the data that a full
  horizon window is observable; customers without a complete horizon are
  excluded from the gold table (censored).
- Reported churn rate and model metrics will differ from the README's figures,
  which were produced under the old definition.
