-- Silver: typed order reviews, real and synthetic combined, then
-- deduplicated to one row per review_id (the raw export repeats some ids).
with src as (
    select
        review_id, order_id, review_score, review_creation_date,
        review_answer_timestamp
    from {{ source('raw', 'olist_order_reviews') }}
    union all
    select
        review_id, order_id, review_score, review_creation_date,
        review_answer_timestamp
    from {{ source('synthetic', 'order_reviews') }}
),
deduped as (
    select
        *,
        row_number() over (
            partition by review_id
            order by nullif(review_answer_timestamp, '')::timestamp desc nulls last
        ) as _rn
    from src
)
select
    review_id,
    order_id,
    review_score::int                              as review_score,
    nullif(review_creation_date, '')::timestamp    as review_creation_date,
    nullif(review_answer_timestamp, '')::timestamp as review_answer_timestamp
from deduped
where _rn = 1
