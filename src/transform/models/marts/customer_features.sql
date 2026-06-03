/*
  Gold table: one feature snapshot per customer as of var('snapshot_date').

  Point-in-time correctness (see docs/adr/0002-future-window-churn-label.md):
    - features use only orders with an order date <= snapshot_date
    - the churn label uses only orders in
      (snapshot_date, snapshot_date + horizon_days]
    - `churned` is TRUE when no order falls in that future window

  Each row also carries a deterministic, churn-stratified train/test/
  validation split (70 / 15 / 15).
*/

{{ config(
    post_hook="create index if not exists ix_customer_features_cuid_snapshot on {{ this }} (customer_unique_id, snapshot_date)"
) }}

{% set snapshot_date = var('snapshot_date') %}
{% set horizon_days = var('horizon_days') %}

with co as (
    select * from {{ ref('int_customer_orders') }}
),

-- Feature window: orders on or before the snapshot date.
hist as (
    select *
    from co
    where order_purchase_timestamp::date <= '{{ snapshot_date }}'::date
),

-- Label window: customers with at least one order in the horizon after it.
future_orders as (
    select distinct customer_unique_id
    from co
    where order_purchase_timestamp::date >  '{{ snapshot_date }}'::date
      and order_purchase_timestamp::date <= '{{ snapshot_date }}'::date + {{ horizon_days }}
),

-- Gaps between a customer's consecutive orders within the feature window.
order_gaps as (
    select
        customer_unique_id,
        order_purchase_timestamp::date
          - lag(order_purchase_timestamp::date) over (
                partition by customer_unique_id
                order by order_purchase_timestamp
            ) as gap_days
    from hist
),

interval_stats as (
    select
        customer_unique_id,
        avg(gap_days::numeric)                                         as order_interval_mean,
        stddev_samp(gap_days::numeric)                                 as order_interval_std,
        percentile_cont(0.5) within group (order by gap_days::numeric)  as order_interval_median
    from order_gaps
    where gap_days is not null
    group by 1
),

features as (
    select
        customer_unique_id,
        '{{ snapshot_date }}'::date                                    as snapshot_date,
        max(customer_state)                                            as customer_state,
        count(distinct order_id)                                       as frequency,
        '{{ snapshot_date }}'::date - max(order_purchase_timestamp)::date  as recency_days,
        max(order_purchase_timestamp)::date
            - min(order_purchase_timestamp)::date                      as tenure_days,
        sum(payment_value)                                             as monetary_total,
        avg(payment_value)                                             as monetary_avg,
        avg(item_count::numeric)                                       as avg_items_per_order,
        avg(freight_value)                                             as avg_freight_value,
        avg(review_score)                                              as avg_review_score,
        count(review_score)                                            as review_count,
        avg(delivery_days)                                             as avg_delivery_days,
        avg(distinct_payment_types::numeric)                           as avg_payment_types,
        avg(avg_installments)                                          as avg_installments,
        avg(distinct_sellers::numeric)                                 as avg_sellers_per_order,
        avg(distinct_categories::numeric)                              as avg_categories_per_order
    from hist
    group by 1, 2
),

labeled as (
    select
        f.*,
        i.order_interval_mean,
        i.order_interval_std,
        i.order_interval_median,
        (fo.customer_unique_id is null) as churned
    from features f
    left join interval_stats i using (customer_unique_id)
    left join future_orders  fo using (customer_unique_id)
),

-- Deterministic stratified split: ntile within each churn class, ordered by a
-- stable hash of the customer id, so every class is split exactly 70/15/15.
bucketed as (
    select
        *,
        ntile(100) over (
            partition by churned
            order by hashtextextended(customer_unique_id, 0)
        ) as _bucket
    from labeled
)

select
    customer_unique_id,
    snapshot_date,
    customer_state,
    frequency,
    recency_days,
    tenure_days,
    monetary_total,
    monetary_avg,
    avg_items_per_order,
    avg_freight_value,
    avg_review_score,
    review_count,
    avg_delivery_days,
    avg_payment_types,
    avg_installments,
    avg_sellers_per_order,
    avg_categories_per_order,
    order_interval_mean,
    order_interval_std,
    order_interval_median,
    churned,
    case
        when _bucket <= 70 then 'train'
        when _bucket <= 85 then 'test'
        else 'validation'
    end as split
from bucketed
