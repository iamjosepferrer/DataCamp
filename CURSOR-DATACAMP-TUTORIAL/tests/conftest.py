import os
from collections.abc import AsyncGenerator, Generator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

from app.database import get_session
from app.main import app

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_budget.db"


@pytest.fixture(scope="session", autouse=True)
def set_test_database_url() -> Generator[None, None, None]:
    original_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL
    yield
    if original_url is not None:
        os.environ["DATABASE_URL"] = original_url
    else:
        os.environ.pop("DATABASE_URL", None)

    if os.path.exists("test_budget.db"):
        os.remove("test_budget.db")


@pytest.fixture
async def session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    async with async_session() as db_session:
        yield db_session

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def client(session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_session() -> AsyncGenerator[AsyncSession, None]:
        yield session

    app.dependency_overrides[get_session] = override_get_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as test_client:
        yield test_client

    app.dependency_overrides.clear()
