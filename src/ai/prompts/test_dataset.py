# Test case 1: Service failure — should produce acknowledging tone, NO offer
test_input_service_failure = {
    "customer_id": "cust_8f3a2b1c",
    "churn_probability": 0.87,
    "risk_tier": "critical",
    "shap_factors": [
        {
            "feature_name": "avg_review_score",
            "feature_value": 2.3,
            "shap_value": 0.42
        },
        {
            "feature_name": "avg_delivery_days",
            "feature_value": 18.5,
            "shap_value": 0.31
        },
        {
            "feature_name": "recency_days",
            "feature_value": 95,
            "shap_value": 0.18
        },
        {
            "feature_name": "total_orders",
            "feature_value": 3,
            "shap_value": -0.05
        },
        {
            "feature_name": "avg_order_value",
            "feature_value": 142.50,
            "shap_value": 0.02
        }
    ],
    "customer_context": {
        "first_name": "Marcos",
        "order_count": 3,
        "last_order_date": "2017-04-28",
        "avg_order_value": 142.50,
        "preferred_category": "electronics"
    }
}

# Test case 2: Price/engagement drift — should produce appreciative tone, WITH offer
test_input_price_sensitive = {
    "customer_id": "cust_2d9e7f4a",
    "churn_probability": 0.64,
    "risk_tier": "high",
    "shap_factors": [
        {
            "feature_name": "recency_days",
            "feature_value": 142,
            "shap_value": 0.38
        },
        {
            "feature_name": "avg_order_value_trend",
            "feature_value": -0.35,
            "shap_value": 0.27
        },
        {
            "feature_name": "total_orders",
            "feature_value": 7,
            "shap_value": -0.22
        },
        {
            "feature_name": "avg_review_score",
            "feature_value": 4.6,
            "shap_value": -0.15
        },
        {
            "feature_name": "avg_delivery_days",
            "feature_value": 7.2,
            "shap_value": -0.08
        }
    ],
    "customer_context": {
        "first_name": "Ana",
        "order_count": 7,
        "last_order_date": "2017-03-12",
        "avg_order_value": 68.40,
        "preferred_category": "home_goods"
    }
}

# Test case 3: Ambiguous mid-tier — tests judgment on conflicting signals
test_input_ambiguous = {
    "customer_id": "cust_6b1c4e8d",
    "churn_probability": 0.41,
    "risk_tier": "medium",
    "shap_factors": [
        {
            "feature_name": "recency_days",
            "feature_value": 78,
            "shap_value": 0.22
        },
        {
            "feature_name": "tenure_days",
            "feature_value": 45,
            "shap_value": 0.19
        },
        {
            "feature_name": "avg_delivery_days",
            "feature_value": 11.2,
            "shap_value": 0.08
        },
        {
            "feature_name": "avg_review_score",
            "feature_value": 4.0,
            "shap_value": -0.04
        },
        {
            "feature_name": "category_diversity",
            "feature_value": 1,
            "shap_value": 0.06
        }
    ],
    "customer_context": {
        "first_name": "Beatriz",
        "order_count": 2,
        "last_order_date": "2017-05-15",
        "avg_order_value": 89.90,
        "preferred_category": "beauty"
    }
}


TEST_CASES = [test_input_service_failure, test_input_price_sensitive, test_input_ambiguous]