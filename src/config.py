from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    stripe_secret_key: str
    stripe_webhook_secret: str
    stripe_publishable_key: str

    database_url: str = "sqlite:///./billing.db"
    app_env: str = "development"

    log_level: str = "INFO"
    billing_api_url: str = "http://localhost:8000"

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()

# Base API call pricing
PRICE_PER_API_CALL_CENTS = 1  # $0.01 / call, example

# Unit conversion reference: 1 cent = 10,000 microcents ($1 = 1,000,000 microcents)
MICROCENTS_PER_CENT = 10_000

PRICE_INPUT_TOKEN_MICROCENTS = 30           # 30 microcents per input token ($3.00 / 1M tokens)
PRICE_CACHED_INPUT_TOKEN_MICROCENTS = 3     # 3 microcents per cached input token ($0.30 / 1M tokens)
PRICE_REASONING_TOKEN_MICROCENTS = 150      # 150 microcents per reasoning token ($15.00 / 1M tokens)
PRICE_OUTPUT_TOKEN_MICROCENTS = 150         # 150 microcents per output token ($15.00 / 1M tokens)

