-- Silver: typed order headers, real and synthetic combined. Empty strings
-- are normalised to NULL before casting (timestamps absent for unshipped
-- orders).
with src as (
    select
        order_id, customer_id, order_status, order_purchase_timestamp,
        order_approved_at, order_delivered_carrier_date,
        order_delivered_customer_date, order_estimated_delivery_date
    from {{ source('raw', 'olist_orders') }}
    union all
    select
        order_id, customer_id, order_status, order_purchase_timestamp,
        order_approved_at, order_delivered_carrier_date,
        order_delivered_customer_date, order_estimated_delivery_date
    from {{ source('synthetic', 'orders') }}
)
select
    order_id,
    customer_id,
    order_status,
    nullif(order_purchase_timestamp, '')::timestamp      as order_purchase_timestamp,
    nullif(order_approved_at, '')::timestamp             as order_approved_at,
    nullif(order_delivered_carrier_date, '')::timestamp  as order_delivered_carrier_date,
    nullif(order_delivered_customer_date, '')::timestamp as order_delivered_customer_date,
    nullif(order_estimated_delivery_date, '')::timestamp as order_estimated_delivery_date
from src
where nullif(order_purchase_timestamp, '') is not null
