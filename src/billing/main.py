"""FastAPI app entrypoint — mounts usage/webhooks/checkout routers."""

from fastapi import FastAPI

app = FastAPI(title="Usage Metering & Billing")

# TODO: app.include_router(usage.router); app.include_router(webhooks.router); ...


def run() -> None:
    import uvicorn

    uvicorn.run("billing.main:app", reload=True)
