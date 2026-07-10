# Budget Tracker API

FastAPI budget tracker with SQLModel and async SQLite.

## Setup

```bash
uv sync
cp .env.example .env
```

## Run

```bash
uv run python main.py
```

Or:

```bash
uv run uvicorn app.main:app --reload
```

API docs: http://localhost:8000/docs

## Test

```bash
uv run pytest tests/ -v
uv run ruff check .
```
