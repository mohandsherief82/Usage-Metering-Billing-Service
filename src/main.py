from fastapi import FastAPI

from src.api.usage import usage_router
from src.api.webhooks import webhook_router

app = FastAPI(title="Usage Metering & Billing")


app.include_router(usage_router)
app.include_router(webhook_router)


def run() -> None:
    import uvicorn

    uvicorn.run("main:app", reload=True)
