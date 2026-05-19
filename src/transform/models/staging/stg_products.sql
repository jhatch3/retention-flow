-- Silver: products, reduced to the identity and category used downstream.
select
    product_id,
    nullif(product_category_name, '') as product_category_name
from {{ source('raw', 'olist_products') }}
