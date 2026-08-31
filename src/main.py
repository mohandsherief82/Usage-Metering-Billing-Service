from fastapi import FastAPI

from src.api.usage import usage_router
from src.api.webhooks import webhook_router
from src.api.checkout import checkout_router

app = FastAPI(title="Usage Metering & Billing")


app.include_router(usage_router)
app.include_router(webhook_router)
app.include_router(checkout_router)


def run() -> None:
    import uvicorn

    uvicorn.run("main:app", reload=True)
