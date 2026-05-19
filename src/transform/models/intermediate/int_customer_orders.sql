-- Silver: the wide order table. One row per order, enriched with the stable
-- customer identity and per-order rollups of items, payments, and reviews.
-- This is the single grain the gold table aggregates from.

with orders as (
    select * from {{ ref('stg_orders') }}
),

customers as (
    select * from {{ ref('stg_customers') }}
),

items as (
    select
        order_id,
        count(*)                    as item_count,
        sum(price)                  as items_value,
        sum(freight_value)          as freight_value,
        count(distinct seller_id)   as distinct_sellers
    from {{ ref('stg_order_items') }}
    group by 1
),

item_categories as (
    select
        oi.order_id,
        count(distinct p.product_category_name) as distinct_categories
    from {{ ref('stg_order_items') }} oi
    left join {{ ref('stg_products') }} p using (product_id)
    group by 1
),

payments as (
    select
        order_id,
        sum(payment_value)               as payment_value,
        count(distinct payment_type)     as distinct_payment_types,
        avg(payment_installments::numeric) as avg_installments
    from {{ ref('stg_order_payments') }}
    group by 1
),

reviews as (
    select
        order_id,
        avg(review_score::numeric) as review_score
    from {{ ref('stg_order_reviews') }}
    group by 1
)

select
    o.order_id,
    c.customer_unique_id,
    c.customer_state,
    o.order_status,
    o.order_purchase_timestamp,
    o.order_delivered_customer_date,
    coalesce(i.item_count, 0)              as item_count,
    coalesce(i.items_value, 0)             as items_value,
    coalesce(i.freight_value, 0)           as freight_value,
    coalesce(i.distinct_sellers, 0)        as distinct_sellers,
    coalesce(ic.distinct_categories, 0)    as distinct_categories,
    coalesce(p.payment_value, 0)           as payment_value,
    coalesce(p.distinct_payment_types, 0)  as distinct_payment_types,
    p.avg_installments,
    r.review_score,
    -- delivery duration in days (NULL when the order was never delivered)
    extract(epoch from (o.order_delivered_customer_date - o.order_purchase_timestamp))
        / 86400.0                          as delivery_days
from orders o
join customers c on o.customer_id = c.customer_id
left join items i on o.order_id = i.order_id
left join item_categories ic on o.order_id = ic.order_id
left join payments p on o.order_id = p.order_id
left join reviews r on o.order_id = r.order_id
