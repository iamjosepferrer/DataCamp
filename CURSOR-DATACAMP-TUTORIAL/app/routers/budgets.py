from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.database import get_session
from app.models import Budget, BudgetCreate, BudgetRead, BudgetUpdate

router = APIRouter(prefix="/budgets", tags=["budgets"])


@router.get("", response_model=list[BudgetRead])
async def list_budgets(session: AsyncSession = Depends(get_session)) -> list[Budget]:
    result = await session.execute(select(Budget))
    return list(result.scalars().all())


@router.post("", response_model=BudgetRead, status_code=status.HTTP_201_CREATED)
async def create_budget(
    budget_in: BudgetCreate,
    session: AsyncSession = Depends(get_session),
) -> Budget:
    budget = Budget.model_validate(budget_in)
    session.add(budget)
    await session.commit()
    await session.refresh(budget)
    return budget


@router.get("/{budget_id}", response_model=BudgetRead)
async def get_budget(
    budget_id: int,
    session: AsyncSession = Depends(get_session),
) -> Budget:
    budget = await session.get(Budget, budget_id)
    if budget is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found",
        )
    return budget


@router.patch("/{budget_id}", response_model=BudgetRead)
async def update_budget(
    budget_id: int,
    budget_in: BudgetUpdate,
    session: AsyncSession = Depends(get_session),
) -> Budget:
    budget = await session.get(Budget, budget_id)
    if budget is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found",
        )

    update_data = budget_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(budget, field, value)

    session.add(budget)
    await session.commit()
    await session.refresh(budget)
    return budget


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_budget(
    budget_id: int,
    session: AsyncSession = Depends(get_session),
) -> None:
    budget = await session.get(Budget, budget_id)
    if budget is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found",
        )

    await session.delete(budget)
    await session.commit()
