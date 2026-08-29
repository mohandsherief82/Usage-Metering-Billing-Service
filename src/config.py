from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    stripe_secret_key: str
    stripe_webhook_secret: str
    stripe_publishable_key: str
    database_url: str = "sqlite:///./billing.db"
    app_env: str = "development"

    class Config:
        env_file = ".env"


settings = Settings()


PRICE_PER_API_CALL_CENTS = 1  # $0.01 / call, example

MICROCENTS_PER_CENT = 10_000

PRICE_INPUT_TOKEN_MICROCENTS = 30
PRICE_CACHED_INPUT_TOKEN_MICROCENTS = 3
PRICE_REASONING_TOKEN_MICROCENTS = 150
PRICE_OUTPUT_TOKEN_MICROCENTS = 150

