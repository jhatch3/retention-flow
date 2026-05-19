"""Mock data for the Triage Inbox (v1).

The Inbox serves this fixture set until the real wiring lands in v1.1 — gold-table
sourcing, LLM-drafted emails, and live DistilBERT/judge eval. Each record is the
full per-customer detail; ``inbox.py`` projects the queue summary from it and
computes the tier, eval pass/fail, and totals so nothing is duplicated here.

See HANDOFF-triage-inbox.md §4 for the field contract.
"""

from __future__ import annotations

# One dict per at-risk customer — ordered loosely; inbox.py re-sorts by risk.
INBOX_CUSTOMERS: list[dict] = [
    {
        "customer_unique_id": "a1b2c3d4e5f6a7b8",
        "display_name": "Camila Ribeiro",
        "city": "São Paulo, SP",
        "ltv_brl": 1840,
        "risk": 0.91,
        "recency_days": 73,
        "reviews_avg": 2.6,
        "delivery_avg_days": 18.4,
        "orders_lifetime": 7,
        "joined_human": "16 mo",
        "last_order_label": "Running shoes · R$ 219",
        "status": "open",
        "email_sent_at": None,
        "cohort_label": "slow-delivery · loyal",
        "cohort_save_rate_pct": 31,
        "cohort_n": 240,
        "drivers": [
            {"feature": "avg_review_score", "value": "2.6", "contrib": 0.42,
             "why": "Recent reviews fell well below her own history and the cohort median."},
            {"feature": "avg_delivery_days", "value": "18.4d", "contrib": 0.28,
             "why": "Deliveries run about a week slower than when she joined."},
            {"feature": "recency_days", "value": "73d", "contrib": 0.19,
             "why": "No order in 73 days — past her usual 40-day reorder rhythm."},
            {"feature": "avg_freight_cost", "value": "R$ 34", "contrib": 0.08,
             "why": "Freight crept up on her last two orders."},
            {"feature": "order_count_lifetime", "value": "7", "contrib": -0.07,
             "why": "Seven lifetime orders still marks a loyal account."},
            {"feature": "category_diversity", "value": "4", "contrib": -0.11,
             "why": "Shops across four categories — breadth usually signals stickiness."},
        ],
        "history": [
            {"ts": "2026-03-06T14:20:00Z", "ts_human": "73d ago",
             "title": "Last order — running shoes", "note": "R$ 219 · delivered 19 days later",
             "tag": "risk"},
            {"ts": "2026-03-25T09:10:00Z", "ts_human": "54d ago",
             "title": "Left a 2-star review", "note": "“Took forever to arrive.”",
             "tag": "risk"},
            {"ts": "2025-11-02T11:00:00Z", "ts_human": "6 mo ago",
             "title": "Peak month — 3 orders", "note": "Highest spend since joining",
             "tag": "pos"},
            {"ts": "2024-12-18T08:30:00Z", "ts_human": "16 mo ago",
             "title": "First order", "note": None, "tag": "neutral"},
        ],
        "email": {
            "generated_at": "2026-05-18T13:40:00Z",
            "generated_by": "claude-opus-4-5",
            "persona": "empathetic-ops",
            "grounded_on": "avg_review_score",
            "subject": "Making your next order right, Camila",
            "to": "c•••@gmail.com",
            "from_name": "Mariana, Olist Customer Success",
            "body": (
                "Hi Camila,\n\n"
                "Your last order took 19 days to reach you — far longer than it should "
                "have, and we saw your review. That is on us, and we are sorry.\n\n"
                "We have added a R$ 40 credit to your account and moved your address onto "
                "our priority carrier, so your next order should arrive in 5–7 days. We would "
                "love the chance to get it right.\n\n"
                "— Mariana, Olist Customer Success"
            ),
        },
        "eval": {"distilbert_score": 4.6, "distilbert_ms": 22,
                 "judge_score": 4.5, "judge_ms": 1400, "pass_threshold": 4.0},
        "plays": [
            {"id": "apology-credit", "name": "Apology + R$ 40 credit",
             "active": True, "save_rate_pct": 31, "sample_n": 240},
            {"id": "priority-shipping", "name": "Free priority shipping, next order",
             "active": False, "save_rate_pct": 24, "sample_n": 180},
            {"id": "personal-checkin", "name": "Personal check-in call",
             "active": False, "save_rate_pct": 19, "sample_n": 95},
        ],
    },
    {
        "customer_unique_id": "b2c3d4e5f6a7b8c9",
        "display_name": "Diego Fonseca",
        "city": "Rio de Janeiro, RJ",
        "ltv_brl": 2310,
        "risk": 0.87,
        "recency_days": 61,
        "reviews_avg": 3.1,
        "delivery_avg_days": 21.2,
        "orders_lifetime": 9,
        "joined_human": "2 yr",
        "last_order_label": "Coffee maker · R$ 389",
        "status": "open",
        "email_sent_at": None,
        "cohort_label": "slow-delivery · high-value",
        "cohort_save_rate_pct": 28,
        "cohort_n": 165,
        "drivers": [
            {"feature": "avg_delivery_days", "value": "21.2d", "contrib": 0.45,
             "why": "Every recent delivery has run past three weeks."},
            {"feature": "avg_freight_cost", "value": "R$ 41", "contrib": 0.21,
             "why": "Shipping cost has climbed on each of the last three orders."},
            {"feature": "recency_days", "value": "61d", "contrib": 0.17,
             "why": "Quiet for two months after a steady monthly cadence."},
            {"feature": "avg_review_score", "value": "3.1", "contrib": 0.12,
             "why": "Reviews slipping but not yet at a collapse."},
            {"feature": "order_count_lifetime", "value": "9", "contrib": -0.09,
             "why": "A long, consistent order history works in his favour."},
        ],
        "history": [
            {"ts": "2026-03-18T16:00:00Z", "ts_human": "61d ago",
             "title": "Last order — coffee maker", "note": "R$ 389 · delivered 23 days later",
             "tag": "risk"},
            {"ts": "2026-01-09T10:00:00Z", "ts_human": "4 mo ago",
             "title": "Raised a delivery-delay ticket", "note": "Resolved, but late",
             "tag": "risk"},
            {"ts": "2024-05-20T12:00:00Z", "ts_human": "2 yr ago",
             "title": "First order", "note": None, "tag": "neutral"},
        ],
        "email": {
            "generated_at": "2026-05-18T13:41:00Z",
            "generated_by": "claude-opus-4-5",
            "persona": "empathetic-ops",
            "grounded_on": "avg_delivery_days",
            "subject": "We owe you a faster delivery, Diego",
            "to": "d•••@outlook.com",
            "from_name": "Mariana, Olist Customer Success",
            "body": (
                "Hi Diego,\n\n"
                "Two years of orders with us, and lately every one has taken over three "
                "weeks to arrive. That is not the experience you signed up for.\n\n"
                "We have switched your region to our express network and waived freight on "
                "your next order. Thank you for staying with us while we fix this.\n\n"
                "— Mariana, Olist Customer Success"
            ),
        },
        "eval": {"distilbert_score": 4.4, "distilbert_ms": 24,
                 "judge_score": 4.3, "judge_ms": 1520, "pass_threshold": 4.0},
        "plays": [
            {"id": "express-freight-waiver", "name": "Express network + freight waiver",
             "active": True, "save_rate_pct": 28, "sample_n": 165},
            {"id": "apology-credit", "name": "Apology + R$ 40 credit",
             "active": False, "save_rate_pct": 26, "sample_n": 240},
            {"id": "loyalty-tier", "name": "Loyalty-tier upgrade", "active": False,
             "save_rate_pct": 22, "sample_n": 110},
        ],
    },
    {
        "customer_unique_id": "c3d4e5f6a7b8c9d0",
        "display_name": "Larissa Antunes",
        "city": "Belo Horizonte, MG",
        "ltv_brl": 760,
        "risk": 0.74,
        "recency_days": 142,
        "reviews_avg": 4.2,
        "delivery_avg_days": 9.1,
        "orders_lifetime": 4,
        "joined_human": "11 mo",
        "last_order_label": "Yoga mat · R$ 89",
        "status": "open",
        "email_sent_at": None,
        "cohort_label": "lapsed · mid-value",
        "cohort_save_rate_pct": 22,
        "cohort_n": 310,
        "drivers": [
            {"feature": "recency_days", "value": "142d", "contrib": 0.51,
             "why": "Nearly five months since her last order — long past any cadence."},
            {"feature": "order_count_lifetime", "value": "4", "contrib": 0.14,
             "why": "A thin order history gives little loyalty buffer."},
            {"feature": "category_diversity", "value": "2", "contrib": 0.10,
             "why": "Buys in only two categories — easy to churn out of both."},
            {"feature": "avg_review_score", "value": "4.2", "contrib": -0.18,
             "why": "Her reviews are strong — the experience itself is not the problem."},
            {"feature": "avg_delivery_days", "value": "9.1d", "contrib": -0.12,
             "why": "Deliveries have been fast and reliable."},
        ],
        "history": [
            {"ts": "2025-12-27T13:00:00Z", "ts_human": "142d ago",
             "title": "Last order — yoga mat", "note": "R$ 89 · 5-star review", "tag": "risk"},
            {"ts": "2025-09-14T10:00:00Z", "ts_human": "8 mo ago",
             "title": "Two orders in one week", "note": "Activewear restock", "tag": "pos"},
            {"ts": "2025-06-30T09:00:00Z", "ts_human": "11 mo ago",
             "title": "First order", "note": None, "tag": "neutral"},
        ],
        "email": {
            "generated_at": "2026-05-18T13:42:00Z",
            "generated_by": "claude-opus-4-5",
            "persona": "warm-reengage",
            "grounded_on": "recency_days",
            "subject": "Your mat misses you, Larissa",
            "to": "l•••@gmail.com",
            "from_name": "Mariana, Olist Customer Success",
            "body": (
                "Hi Larissa,\n\n"
                "It has been a few months since your last order — and you left us a 5-star "
                "review on that yoga mat, so we hope it is still going strong.\n\n"
                "The activewear brand you bought from just restocked. Here is 15% off if you "
                "would like to refresh your kit before it sells out again.\n\n"
                "— Mariana, Olist Customer Success"
            ),
        },
        "eval": {"distilbert_score": 4.2, "distilbert_ms": 21,
                 "judge_score": 4.4, "judge_ms": 1380, "pass_threshold": 4.0},
        "plays": [
            {"id": "reengage-discount", "name": "15% win-back discount",
             "active": True, "save_rate_pct": 22, "sample_n": 310},
            {"id": "restock-alert", "name": "Favourite-brand restock alert",
             "active": False, "save_rate_pct": 18, "sample_n": 205},
            {"id": "personal-checkin", "name": "Personal check-in call",
             "active": False, "save_rate_pct": 15, "sample_n": 95},
        ],
    },
    {
        "customer_unique_id": "d4e5f6a7b8c9d0e1",
        "display_name": "Rafael Moreira",
        "city": "Porto Alegre, RS",
        "ltv_brl": 1490,
        "risk": 0.68,
        "recency_days": 88,
        "reviews_avg": 3.8,
        "delivery_avg_days": 11.6,
        "orders_lifetime": 12,
        "joined_human": "2 yr",
        "last_order_label": "Desk lamp · R$ 134",
        "status": "sent",
        "email_sent_at": "2026-05-17T15:30:00Z",
        "cohort_label": "declining-frequency · loyal",
        "cohort_save_rate_pct": 26,
        "cohort_n": 198,
        "drivers": [
            {"feature": "order_count_lifetime", "value": "12", "contrib": 0.33,
             "why": "Order frequency has halved versus his first year."},
            {"feature": "recency_days", "value": "88d", "contrib": 0.24,
             "why": "Three months quiet after a once-monthly habit."},
            {"feature": "avg_review_score", "value": "3.8", "contrib": 0.09,
             "why": "Reviews easing down but still broadly positive."},
            {"feature": "avg_delivery_days", "value": "11.6d", "contrib": -0.06,
             "why": "Delivery times are steady and acceptable."},
            {"feature": "category_diversity", "value": "5", "contrib": -0.15,
             "why": "Shops widely across five categories — a sticky pattern."},
        ],
        "history": [
            {"ts": "2026-02-19T11:00:00Z", "ts_human": "88d ago",
             "title": "Last order — desk lamp", "note": "R$ 134", "tag": "risk"},
            {"ts": "2026-05-17T15:30:00Z", "ts_human": "1d ago",
             "title": "Retention email sent", "note": "Win-back · awaiting reply",
             "tag": "neutral"},
            {"ts": "2024-04-11T09:00:00Z", "ts_human": "2 yr ago",
             "title": "First order", "note": None, "tag": "neutral"},
        ],
        "email": {
            "generated_at": "2026-05-17T15:28:00Z",
            "generated_by": "claude-opus-4-5",
            "persona": "warm-reengage",
            "grounded_on": "order_count_lifetime",
            "subject": "A little something for a long-time customer",
            "to": "r•••@gmail.com",
            "from_name": "Mariana, Olist Customer Success",
            "body": (
                "Hi Rafael,\n\n"
                "Two years and a dozen orders later, we noticed it has been a quiet few "
                "months — and we did not want that to pass without saying thank you.\n\n"
                "Here is free shipping on your next order, plus early access to the lighting "
                "range you have ordered from before.\n\n"
                "— Mariana, Olist Customer Success"
            ),
        },
        "eval": {"distilbert_score": 4.5, "distilbert_ms": 23,
                 "judge_score": 4.4, "judge_ms": 1460, "pass_threshold": 4.0},
        "plays": [
            {"id": "loyalty-thanks", "name": "Loyalty thank-you + free shipping",
             "active": True, "save_rate_pct": 26, "sample_n": 198},
            {"id": "reengage-discount", "name": "15% win-back discount",
             "active": False, "save_rate_pct": 21, "sample_n": 310},
            {"id": "early-access", "name": "Early access to new range",
             "active": False, "save_rate_pct": 17, "sample_n": 140},
        ],
    },
    {
        "customer_unique_id": "e5f6a7b8c9d0e1f2",
        "display_name": "Beatriz Carvalho",
        "city": "Curitiba, PR",
        "ltv_brl": 540,
        "risk": 0.51,
        "recency_days": 47,
        "reviews_avg": 3.5,
        "delivery_avg_days": 13.0,
        "orders_lifetime": 5,
        "joined_human": "14 mo",
        "last_order_label": "Backpack · R$ 159",
        "status": "open",
        "email_sent_at": None,
        "cohort_label": "price-sensitive · mid-value",
        "cohort_save_rate_pct": 20,
        "cohort_n": 275,
        "drivers": [
            {"feature": "avg_freight_cost", "value": "R$ 38", "contrib": 0.29,
             "why": "Freight has been a rising share of every order total."},
            {"feature": "avg_review_score", "value": "3.5", "contrib": 0.13,
             "why": "Reviews mention shipping cost more than the products."},
            {"feature": "recency_days", "value": "47d", "contrib": 0.10,
             "why": "Slightly past her usual six-week cadence."},
            {"feature": "order_count_lifetime", "value": "5", "contrib": -0.05,
             "why": "A modest but steady order history."},
            {"feature": "avg_delivery_days", "value": "13.0d", "contrib": -0.08,
             "why": "Delivery speed is unremarkable — not a driver of risk."},
        ],
        "history": [
            {"ts": "2026-04-01T14:00:00Z", "ts_human": "47d ago",
             "title": "Last order — backpack", "note": "R$ 159 · R$ 38 freight", "tag": "risk"},
            {"ts": "2026-02-10T10:00:00Z", "ts_human": "3 mo ago",
             "title": "Abandoned a cart", "note": "Removed item at checkout", "tag": "risk"},
            {"ts": "2025-03-22T09:00:00Z", "ts_human": "14 mo ago",
             "title": "First order", "note": None, "tag": "neutral"},
        ],
        "email": {
            "generated_at": "2026-05-18T13:43:00Z",
            "generated_by": "claude-opus-4-5",
            "persona": "value-forward",
            "grounded_on": "avg_freight_cost",
            "subject": "Free shipping on your next order, Beatriz",
            "to": "b•••@gmail.com",
            "from_name": "Mariana, Olist Customer Success",
            "body": (
                "Hi Beatriz,\n\n"
                "We noticed shipping has been adding up on your recent orders — and that is "
                "an easy thing for us to fix.\n\n"
                "Your next order ships free, no minimum. The bags and travel range you browse "
                "most are linked below.\n\n"
                "— Mariana, Olist Customer Success"
            ),
        },
        "eval": {"distilbert_score": 4.1, "distilbert_ms": 22,
                 "judge_score": 4.2, "judge_ms": 1340, "pass_threshold": 4.0},
        "plays": [
            {"id": "free-shipping", "name": "Free shipping, next order",
             "active": True, "save_rate_pct": 20, "sample_n": 275},
            {"id": "reengage-discount", "name": "15% win-back discount",
             "active": False, "save_rate_pct": 19, "sample_n": 310},
            {"id": "bundle-offer", "name": "Bundle discount", "active": False,
             "save_rate_pct": 14, "sample_n": 160},
        ],
    },
    {
        "customer_unique_id": "f6a7b8c9d0e1f2a3",
        "display_name": "Thiago Nunes",
        "city": "Salvador, BA",
        "ltv_brl": 320,
        "risk": 0.39,
        "recency_days": 38,
        "reviews_avg": 4.0,
        "delivery_avg_days": 10.4,
        "orders_lifetime": 3,
        "joined_human": "7 mo",
        "last_order_label": "Phone case · R$ 49",
        "status": "open",
        "email_sent_at": None,
        "cohort_label": "single-category · low-value",
        "cohort_save_rate_pct": 16,
        "cohort_n": 420,
        "drivers": [
            {"feature": "category_diversity", "value": "1", "contrib": 0.27,
             "why": "Every order has been in a single category — no breadth to fall back on."},
            {"feature": "order_count_lifetime", "value": "3", "contrib": 0.15,
             "why": "Only three orders — not yet an established habit."},
            {"feature": "recency_days", "value": "38d", "contrib": 0.06,
             "why": "Just past a typical reorder window."},
            {"feature": "avg_review_score", "value": "4.0", "contrib": -0.10,
             "why": "Solid reviews — the experience is fine."},
            {"feature": "avg_delivery_days", "value": "10.4d", "contrib": -0.07,
             "why": "Delivery has been reliably on time."},
        ],
        "history": [
            {"ts": "2026-04-10T12:00:00Z", "ts_human": "38d ago",
             "title": "Last order — phone case", "note": "R$ 49", "tag": "risk"},
            {"ts": "2025-10-15T09:00:00Z", "ts_human": "7 mo ago",
             "title": "First order", "note": None, "tag": "neutral"},
        ],
        "email": {
            "generated_at": "2026-05-18T13:44:00Z",
            "generated_by": "claude-opus-4-5",
            "persona": "discovery",
            "grounded_on": "category_diversity",
            "subject": "A few things we think you'll like, Thiago",
            "to": "t•••@hotmail.com",
            "from_name": "Mariana, Olist Customer Success",
            "body": (
                "Hi Thiago,\n\n"
                "Thanks for your recent orders. We have picked a few things beyond phone "
                "accessories that pair well with what you have bought.\n\n"
                "Have a browse when you have a moment — returning customers get 10% off the "
                "first order in a new category.\n\n"
                "— Mariana, Olist Customer Success"
            ),
        },
        "eval": {"distilbert_score": 3.9, "distilbert_ms": 22,
                 "judge_score": 3.6, "judge_ms": 1290, "pass_threshold": 4.0},
        "plays": [
            {"id": "cross-category", "name": "Cross-category discovery + 10% off",
             "active": True, "save_rate_pct": 16, "sample_n": 420},
            {"id": "reengage-discount", "name": "15% win-back discount",
             "active": False, "save_rate_pct": 15, "sample_n": 310},
            {"id": "bundle-offer", "name": "Bundle discount", "active": False,
             "save_rate_pct": 12, "sample_n": 160},
        ],
    },
    {
        "customer_unique_id": "a7b8c9d0e1f2a3b4",
        "display_name": "Mariana Lopes",
        "city": "Recife, PE",
        "ltv_brl": 980,
        "risk": 0.27,
        "recency_days": 19,
        "reviews_avg": 4.7,
        "delivery_avg_days": 8.2,
        "orders_lifetime": 8,
        "joined_human": "18 mo",
        "last_order_label": "Cookware set · R$ 274",
        "status": "open",
        "email_sent_at": None,
        "cohort_label": "healthy · loyal",
        "cohort_save_rate_pct": 12,
        "cohort_n": 530,
        "drivers": [
            {"feature": "recency_days", "value": "19d", "contrib": 0.11,
             "why": "A recent order — only a mild recency signal."},
            {"feature": "avg_freight_cost", "value": "R$ 22", "contrib": 0.05,
             "why": "Freight is low and steady."},
            {"feature": "avg_review_score", "value": "4.7", "contrib": -0.22,
             "why": "Consistently high reviews — a strongly protective signal."},
            {"feature": "category_diversity", "value": "6", "contrib": -0.17,
             "why": "Shops across six categories — broad, sticky engagement."},
            {"feature": "avg_delivery_days", "value": "8.2d", "contrib": -0.09,
             "why": "Fast, dependable deliveries."},
        ],
        "history": [
            {"ts": "2026-04-29T10:00:00Z", "ts_human": "19d ago",
             "title": "Last order — cookware set", "note": "R$ 274 · 5-star review",
             "tag": "pos"},
            {"ts": "2026-02-02T09:00:00Z", "ts_human": "3 mo ago",
             "title": "Referred a friend", "note": "Referral order placed", "tag": "pos"},
            {"ts": "2024-11-08T09:00:00Z", "ts_human": "18 mo ago",
             "title": "First order", "note": None, "tag": "neutral"},
        ],
        "email": {
            "generated_at": "2026-05-18T13:45:00Z",
            "generated_by": "claude-opus-4-5",
            "persona": "warm-reengage",
            "grounded_on": "avg_review_score",
            "subject": "Thank you for being a regular, Mariana",
            "to": "m•••@gmail.com",
            "from_name": "Mariana, Olist Customer Success",
            "body": (
                "Hi Mariana,\n\n"
                "You are one of our most consistent customers — eight orders, glowing "
                "reviews, and a referral. Thank you.\n\n"
                "There is nothing to fix here; just a small thank-you: early access to the "
                "kitchen range you shop most.\n\n"
                "— Mariana, Olist Customer Success"
            ),
        },
        "eval": {"distilbert_score": 4.7, "distilbert_ms": 21,
                 "judge_score": 4.6, "judge_ms": 1410, "pass_threshold": 4.0},
        "plays": [
            {"id": "loyalty-thanks", "name": "Loyalty thank-you + early access",
             "active": True, "save_rate_pct": 12, "sample_n": 530},
            {"id": "referral-bonus", "name": "Referral bonus", "active": False,
             "save_rate_pct": 10, "sample_n": 300},
            {"id": "no-action", "name": "No action — monitor", "active": False,
             "save_rate_pct": 0, "sample_n": 0},
        ],
    },
]
