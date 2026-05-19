-- Silver: typed order payments (one row per payment on an order),
-- real and synthetic combined.
with src as (
    select
        order_id, payment_sequential, payment_type,
        payment_installments, payment_value
    from {{ source('raw', 'olist_order_payments') }}
    union all
    select
        order_id, payment_sequential, payment_type,
        payment_installments, payment_value
    from {{ source('synthetic', 'order_payments') }}
)
select
    order_id,
    payment_sequential::int            as payment_sequential,
    payment_type,
    payment_installments::int          as payment_installments,
    nullif(payment_value, '')::numeric as payment_value
from src
