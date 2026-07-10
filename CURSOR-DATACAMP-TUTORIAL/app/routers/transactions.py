from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.database import get_session
from app.models import (
    Budget,
    Transaction,
    TransactionCreate,
    TransactionRead,
)

router = APIRouter(prefix="/budgets", tags=["transactions"])


@router.get("/{budget_id}/transactions", response_model=list[TransactionRead])
async def list_transactions(
    budget_id: int,
    session: AsyncSession = Depends(get_session),
) -> list[Transaction]:
    budget = await session.get(Budget, budget_id)
    if budget is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found",
        )

    result = await session.execute(
        select(Transaction).where(Transaction.budget_id == budget_id)
    )
    return list(result.scalars().all())


@router.post(
    "/{budget_id}/transactions",
    response_model=TransactionRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_transaction(
    budget_id: int,
    transaction_in: TransactionCreate,
    session: AsyncSession = Depends(get_session),
) -> Transaction:
    budget = await session.get(Budget, budget_id)
    if budget is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found",
        )

    transaction = Transaction.model_validate(
        transaction_in, update={"budget_id": budget_id}
    )
    session.add(transaction)
    await session.commit()
    await session.refresh(transaction)
    return transaction
