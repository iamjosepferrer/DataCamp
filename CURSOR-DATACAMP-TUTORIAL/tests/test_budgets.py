import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_create_and_get_budget(client: AsyncClient) -> None:
    create_response = await client.post(
        "/api/v1/budgets",
        json={
            "name": "Groceries",
            "description": "Monthly food budget",
            "limit_amount": "500.00",
        },
    )
    assert create_response.status_code == 201
    budget = create_response.json()
    assert budget["name"] == "Groceries"
    assert budget["limit_amount"] == "500.00"
    assert "id" in budget

    get_response = await client.get(f"/api/v1/budgets/{budget['id']}")
    assert get_response.status_code == 200
    assert get_response.json()["name"] == "Groceries"


@pytest.mark.asyncio
async def test_list_budgets(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/budgets",
        json={"name": "Transport", "limit_amount": "200.00"},
    )

    response = await client.get("/api/v1/budgets")
    assert response.status_code == 200
    assert len(response.json()) >= 1


@pytest.mark.asyncio
async def test_create_transaction(client: AsyncClient) -> None:
    budget_response = await client.post(
        "/api/v1/budgets",
        json={"name": "Entertainment", "limit_amount": "150.00"},
    )
    budget_id = budget_response.json()["id"]

    transaction_response = await client.post(
        f"/api/v1/budgets/{budget_id}/transactions",
        json={
            "amount": "25.50",
            "description": "Movie tickets",
            "type": "expense",
        },
    )
    assert transaction_response.status_code == 201
    transaction = transaction_response.json()
    assert transaction["budget_id"] == budget_id
    assert transaction["amount"] == "25.50"

    list_response = await client.get(f"/api/v1/budgets/{budget_id}/transactions")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1
