-- Silver: one row per Olist customer instance, real and synthetic combined.
-- `customer_id` is per-order; `customer_unique_id` is the stable person id.
with src as (
    select
        customer_id, customer_unique_id, customer_zip_code_prefix,
        customer_city, customer_state
    from {{ source('raw', 'olist_customers') }}
    union all
    select
        customer_id, customer_unique_id, customer_zip_code_prefix,
        customer_city, customer_state
    from {{ source('synthetic', 'customers') }}
)
select
    customer_id,
    customer_unique_id,
    customer_zip_code_prefix,
    customer_city,
    upper(customer_state) as customer_state
from src
