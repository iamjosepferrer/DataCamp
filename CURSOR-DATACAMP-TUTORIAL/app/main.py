from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI

from app.database import init_db
from app.routers import budgets, transactions


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    await init_db()
    yield


app = FastAPI(title="Budget Tracker API", lifespan=lifespan)

app.include_router(budgets.router, prefix="/api/v1")
app.include_router(transactions.router, prefix="/api/v1")


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
