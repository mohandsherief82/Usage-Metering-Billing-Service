from fastapi import FastAPI
from src.api.usage import usage_router

app = FastAPI(title="Usage Metering & Billing")

# TODO: app.include_router(webhooks.router); ...
app.include_router(usage_router)


def run() -> None:
    import uvicorn

    uvicorn.run("billing.main:app", reload=True)
