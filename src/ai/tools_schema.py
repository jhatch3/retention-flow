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


TOOL_SCHEMAS = [
    get_current_datetime_schema,
]
