# Synthetic repeat-order augmentation

Olist is a near-pure single-purchase marketplace — across the whole dataset
only ~3% of customers ever place a second order. That makes any churn or
retention label degenerate: an honest future-window label is ~98% positive,
so a model has nothing to learn. To make churn a viable ML target, a one-time
simulation augments the data with synthetic repeat orders.

Reorder behaviour is **signal-driven**: each customer's propensity to return
is a function of their *real* first-order experience — a high review score
and fast delivery raise it, slow delivery lowers it — plus noise. The churn
model therefore learns a genuine relationship rather than noise. Synthetic
rows are written to a separate `synthetic` schema; the `raw` schema stays a
verbatim copy of Olist, and dbt staging models `union all` the two sources.

## Consequences

- The training data is **Olist augmented with simulation**, not pure Olist.
  Any reported metric must be presented as such — this is not a result on
  real customer behaviour.
- The generator is seeded, so the augmentation is reproducible.
- Lineage stays honest: real vs synthetic rows are separable by schema.
