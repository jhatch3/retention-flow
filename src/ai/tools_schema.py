get_current_datetime_schema = {
    "name": "get_current_datetime",
    "description": "Returns the current date and time in the specified IANA timezone. Use this whenever the user asks about the current time, today's date, or needs a timestamp. Defaults to UTC if no timezone is provided.",
    "input_schema": {
        "type": "object",
        "properties": {
            "timezone": {
                "type": "string",
                "description": "IANA timezone name (e.g., 'America/Los_Angeles', 'Europe/London', 'Asia/Tokyo'). Defaults to 'UTC'.",
            }
        },
        "required": [],
    },
}
                  
FORMAT_RESPONSE_OUTPUT_CONFIG = {
    "format": {
        "type": "json_schema",
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "customer_id",
                "subject",
                "body",
                "call_to_action",
                "tone",
                "risk_tier",
                "includes_offer",
                "grounding",
                "reasoning",
            ],
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "Echo the customer_id from the input payload verbatim.",
                },
                "subject": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 60,
                    "description": "Email subject line. Under 60 characters. No emojis.",
                },
                "body": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 1200,
                    "description": (
                        "Plain text email body. Use \\n for line breaks. Under 150 words "
                        "unless the situation genuinely requires more. Address the customer "
                        "by first name once in the greeting. Sign off as 'The [Brand] Team'."
                    ),
                },
                "call_to_action": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["text", "intent"],
                    "properties": {
                        "text": {
                            "type": "string",
                            "minLength": 1,
                            "maxLength": 30,
                            "description": "Button or link text. Under 30 characters.",
                        },
                        "intent": {
                            "type": "string",
                            "enum": ["browse", "support", "reorder", "redeem", "feedback"],
                            "description": (
                                "The CTA's underlying purpose. 'support' for service-failure "
                                "cases, 'redeem' when including an offer, 'reorder' for "
                                "lapsed-but-happy customers, 'browse' for soft re-engagement, "
                                "'feedback' for diagnostic outreach."
                            ),
                        },
                    },
                },
                "tone": {
                    "type": "string",
                    "enum": ["neutral", "acknowledging", "reassuring", "appreciative"],
                    "description": (
                        "The email's strategic tone. 'acknowledging' for service failures, "
                        "'reassuring' for hesitant customers, 'appreciative' for valued "
                        "lapsed customers, 'neutral' as the default professional baseline."
                    ),
                },
                "risk_tier": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "critical"],
                    "description": "Echo the risk_tier from the input payload verbatim.",
                },
                "includes_offer": {
                    "type": "boolean",
                    "description": (
                        "True if the email body includes a promotional offer (discount, "
                        "free shipping, credit). False otherwise. Must reflect what is "
                        "actually in the body field."
                    ),
                },
                "grounding": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["shap_factors_addressed", "factors_intentionally_ignored"],
                    "properties": {
                        "shap_factors_addressed": {
                            "type": "array",
                            "description": "SHAP factors the email actually surfaces or responds to. 1-5 items.",
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "required": ["feature_name", "shap_value", "how_addressed"],
                                "properties": {
                                    "feature_name": {
                                        "type": "string",
                                        "description": "Feature name copied verbatim from input.",
                                    },
                                    "shap_value": {
                                        "type": "number",
                                        "description": "SHAP value copied verbatim from input.",
                                    },
                                    "how_addressed": {
                                        "type": "string",
                                        "minLength": 1,
                                        "maxLength": 300,
                                        "description": (
                                            "One sentence describing how this factor shaped "
                                            "the email content. Must reference something "
                                            "concrete in the body."
                                        ),
                                    },
                                },
                            },
                        },
                        "factors_intentionally_ignored": {
                            "type": "array",
                            "description": (
                                "SHAP factors present in the input but deliberately not "
                                "surfaced in the email. Up to 5 items. Empty array is valid "
                                "if all factors were addressed."
                            ),
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "required": ["feature_name", "reason"],
                                "properties": {
                                    "feature_name": {
                                        "type": "string",
                                        "description": "Feature name copied verbatim from input.",
                                    },
                                    "reason": {
                                        "type": "string",
                                        "minLength": 1,
                                        "maxLength": 300,
                                        "description": (
                                            "One sentence explaining why this factor was "
                                            "not surfaced (e.g., not actionable, awkward "
                                            "to mention, protective rather than risk-driving)."
                                        ),
                                    },
                                },
                            },
                        },
                    },
                },
                "reasoning": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 800,
                    "description": (
                        "2-3 sentences explaining the strategic choice: why this tone, why "
                        "offer/no-offer, why these factors. Honest reasoning for the eval "
                        "framework, not marketing language."
                    ),
                },
            },
        },
    }
}


GRADER_OUTPUT_CONFIG = {
    "format": {
        "type": "json_schema",
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "test_case_name",
                "score",
                "success_criteria",
                "clauses_evaluated",
                "weaknesses",
                "reasoning",
                "certainty",
            ],
            "properties": {
                "test_case_name": {
                    "type": "string",
                    "description": "Echo the test_case_name from the input verbatim.",
                },
                "score": {
                    "type": "number",
                    "description": (
                        "Score from 1 (fails all criteria) to 10 (essentially never awarded; reserved "
                        "for publishable-as-is with creative strength). Fractional scores allowed. "
                        "Default is 6. Competent baseline is 7. See rubric and hard caps in the "
                        "system prompt. Must be between 1 and 10."
                    ),
                },
                "success_criteria": {
                    "type": "string",
                    "description": "Echo the success_criteria from the input verbatim.",
                },
                "clauses_evaluated": {
                    "type": "array",
                    "description": (
                        "One entry per distinct clause in success_criteria. You must produce at "
                        "least one entry per clause — do not collapse multiple clauses into one."
                    ),
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["clause", "verdict", "evidence"],
                        "properties": {
                            "clause": {
                                "type": "string",
                                "description": "Paraphrase of the clause from success_criteria.",
                            },
                            "verdict": {
                                "type": "string",
                                "enum": ["met", "partially_met", "not_met", "not_assessable"],
                                "description": "How this clause was honored by the email.",
                            },
                            "evidence": {
                                "type": "string",
                                "description": (
                                    "Specific quoted phrase from the email body OR specific field "
                                    "value from generated_email backing the verdict."
                                ),
                            },
                        },
                    },
                },
                "weaknesses": {
                    "type": "array",
                    "description": (
                        "At least 2 specific weaknesses or risks in the email. Quote phrases or "
                        "point at field values. Even strong emails have weaknesses — find them. "
                        "Subject-line genericness, unfilled placeholders, awkward sentences, and "
                        "weak grounding all count."
                    ),
                    "items": {"type": "string"},
                },
                "reasoning": {
                    "type": "string",
                    "description": (
                        "2-5 sentences connecting clauses_evaluated and weaknesses to the final "
                        "score. Apply hard caps explicitly. To award above 7, you must list at "
                        "least three distinct active strengths here."
                    ),
                },
                "certainty": {
                    "type": "number",
                    "description": (
                        "Your confidence in the score. Float between 0 (uncertain) and 1 (very "
                        "certain). See the rubric in the system prompt for calibration anchors."
                    ),
                },
            },
        },
    }
}


get_customer_delivery_stats_schema = {
    "name": "get_customer_delivery_stats",
    "description": (
        "Returns this customer's average delivery time across all their delivered orders, "
        "alongside the marketplace-wide average for comparison. Use this when the SHAP factors "
        "for the email include avg_delivery_days as a risk driver, or when you want to "
        "concretely ground a 'your deliveries have been slow' acknowledgment with real numbers "
        "(e.g., 'your last orders averaged 14 days; our marketplace average is 5'). "
        "Returns null fields if the customer has no delivered orders."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "customer_unique_id": {
                "type": "string",
                "description": "The customer_unique_id from the customer payload (top-level customer_id field).",
            }
        },
        "required": ["customer_unique_id"],
    },
}

get_customer_recent_orders_schema = {
    "name": "get_customer_recent_orders",
    "description": (
        "Returns this customer's most recent orders, with category, delivery_days, order_status, "
        "and avg_review_score per order. Use this when the email could benefit from a concrete "
        "reference to a recent order (e.g., 'your last books order took 14 days and you rated it 2 "
        "stars'). Empty list if the customer has no orders. Default limit is 5."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "customer_unique_id": {
                "type": "string",
                "description": "The customer_unique_id from the customer payload.",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of orders to return (clamped to 1-20). Default 5.",
            },
        },
        "required": ["customer_unique_id"],
    },
}

get_category_baseline_schema = {
    "name": "get_category_baseline",
    "description": (
        "Returns marketplace-wide stats for a product category (avg delivery days, avg review "
        "score, total order count). Use this to make comparative claims like 'books in our "
        "marketplace typically arrive in 6 days'. Accepts the English category name (e.g., "
        "'electronics', 'books_general_interest', 'health_beauty') or the Portuguese name. "
        "Returns null fields with a 'category not found' note if the category isn't recognized."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "description": (
                    "Category name (English preferred). Examples: 'electronics', 'books_general_interest', "
                    "'health_beauty', 'home_appliances'. Pass the customer's preferred_category if you want "
                    "the baseline for their main category."
                ),
            }
        },
        "required": ["category"],
    },
}

get_customer_review_history_schema = {
    "name": "get_customer_review_history",
    "description": (
        "Returns this customer's recent reviews, with score, date, comment title/message, and "
        "category context. Use this when avg_review_score is a SHAP risk driver and you want to "
        "ground the email in the customer's actual review history rather than an aggregate "
        "number. Empty list if the customer has no reviews. Default limit is 10."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "customer_unique_id": {
                "type": "string",
                "description": "The customer_unique_id from the customer payload.",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of reviews to return (clamped to 1-25). Default 10.",
            },
        },
        "required": ["customer_unique_id"],
    },
}


TOOL_SCHEMAS = [
    get_current_datetime_schema,
    get_customer_delivery_stats_schema,
    get_customer_recent_orders_schema,
    get_category_baseline_schema,
    get_customer_review_history_schema,
]
