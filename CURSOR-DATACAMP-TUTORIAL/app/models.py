from datetime import datetime
from decimal import Decimal
from enum import Enum

from sqlmodel import Field, SQLModel


class TransactionType(str, Enum):
    INCOME = "income"
    EXPENSE = "expense"


class BudgetBase(SQLModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    limit_amount: Decimal = Field(gt=0, decimal_places=2)


class Budget(BudgetBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class BudgetCreate(BudgetBase):
    pass


class BudgetRead(BudgetBase):
    id: int
    created_at: datetime


class BudgetUpdate(SQLModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    limit_amount: Decimal | None = Field(default=None, gt=0, decimal_places=2)


class TransactionBase(SQLModel):
    amount: Decimal = Field(gt=0, decimal_places=2)
    description: str = Field(min_length=1, max_length=500)
    type: TransactionType


class Transaction(TransactionBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    budget_id: int = Field(foreign_key="budget.id", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class TransactionCreate(TransactionBase):
    pass


class TransactionRead(TransactionBase):
    id: int
    budget_id: int
    created_at: datetime
