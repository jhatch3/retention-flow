-- Silver: typed order line items (one row per item within an order),
-- real and synthetic combined.
with src as (
    select
        order_id, order_item_id, product_id, seller_id,
        shipping_limit_date, price, freight_value
    from {{ source('raw', 'olist_order_items') }}
    union all
    select
        order_id, order_item_id, product_id, seller_id,
        shipping_limit_date, price, freight_value
    from {{ source('synthetic', 'order_items') }}
)
select
    order_id,
    order_item_id::int                         as order_item_id,
    product_id,
    seller_id,
    nullif(shipping_limit_date, '')::timestamp as shipping_limit_date,
    nullif(price, '')::numeric                 as price,
    nullif(freight_value, '')::numeric         as freight_value
from src
