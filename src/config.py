"""
Pinned pricing & app configuration.

RULE: every price constant here is an INTEGER (cents, or micro-cents for
per-token pricing) — never a float. Floats introduce rounding drift across
millions of usage events; integers don't.

Fill these in with your own made-up-but-fixed numbers for the capstone.
Cite units in the comment next to each constant, and never let a service
module hardcode a price inline — everything routes through here so
EVIDENCE.md's "pinned in config" requirement has one obvious place to point.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    stripe_secret_key: str
    stripe_webhook_secret: str
    stripe_publishable_key: str
    database_url: str = "sqlite:///./billing.db"
    app_env: str = "development"

    class Config:
        env_file = ".env"


settings = Settings()  # type: ignore[call-arg]  # populated from .env at import time


# --- Pricing constants (cents unless noted) --------------------------------
# API-call style plans
PRICE_PER_API_CALL_CENTS = 1  # $0.01 / call, example

# AI token pricing — micro-cents per token (1 cent = 10_000 micro-cents) so
# sub-cent-per-token prices stay integers. Adjust the scale factor to taste,
# just keep it an int and keep the scale documented.
MICROCENTS_PER_CENT = 10_000

PRICE_INPUT_TOKEN_MICROCENTS = 30          # e.g. $3 / 1M input tokens
PRICE_CACHED_INPUT_TOKEN_MICROCENTS = 3    # cached input priced ~10x cheaper
PRICE_REASONING_TOKEN_MICROCENTS = 150     # reasoning tokens billed like output
PRICE_OUTPUT_TOKEN_MICROCENTS = 150        # e.g. $15 / 1M output tokens

# Plan quotas live in the `plans` DB table, not here — config.py is for
# *pricing* constants that don't vary per tenant/plan row.
