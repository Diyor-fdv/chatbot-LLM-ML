## AI-Powered Analytics Chatbot (Power BI Ready) — Starter Project

Production-style starter for a **safe analytics chatbot**:

- User asks a natural language question
- System maps it to a **controlled analytics intent** using a **semantic layer**
- Builds **read-only SQL via SQLAlchemy** (not free-form LLM SQL)
- Returns:
  - human-readable insight text
  - structured dataset (rows + columns)
  - deterministic chart recommendation
  - filter metadata
  - KPI summary
  - Power BI-friendly visualization metadata

This repo ships with a **PostgreSQL star schema + seed data**, so you can run from 0 → working MVP locally.

---

## Architecture (safe-by-design)

1. **Semantic Layer** (`config/semantic_layer.yml`)
   - Defines approved tables/joins
   - Defines metrics (e.g. `revenue = sum(fact_sales.revenue)`)
   - Defines dimensions (e.g. `city = dim_city.city_name`)
   - Easy to edit for your real schema later
2. **Intent Parsing**
   - Rule-based extraction for date ranges, top-N, group-bys, filters
   - Optional **Agno** LLM assist (OpenAI-compatible via Agno `OpenAIChat`) to improve structured intent
   - LLM output is **validated/whitelisted** (metrics/dimensions/ops)
3. **Query Builder**
   - Builds SQLAlchemy `SELECT` from intent + semantic layer
   - Enforces safe joins, group-bys, sorting, and **LIMIT**
   - Dev-only endpoint supports read-only SQL with safety checks
4. **Response Composer**
   - Computes KPIs
   - Generates insight text (template-first, optional LLM polish)
   - Generates `powerbi.visual.encoding` metadata for client-side rendering

---

## Folder Structure

```
project_root/
  app/
    api/               # FastAPI routes
    core/              # settings, logging, errors
    db/                # engine/session/base
    llm/               # OpenAI-compatible abstraction (optional)
    models/            # SQLAlchemy ORM models
    schemas/           # Pydantic API schemas + internal intent schema
    services/          # semantic layer, parsing, query builder, chart logic
    utils/
    main.py
  alembic/             # migrations
  config/              # semantic_layer.yml
  scripts/             # seed_db.py
  tests/
  Dockerfile
  docker-compose.yml
  requirements.txt
  .env.example
```

---

## Quickstart (Docker — recommended)

### Prereqs
- Docker Desktop

### Run

```bash
docker compose up --build
```

### Run migrations + seed (in a second terminal)

```bash
docker compose exec api alembic upgrade head
docker compose exec api python -m scripts.seed_db
```

API will be available at:
- Swagger UI: `http://localhost:8000/docs`
- Health: `GET http://localhost:8000/health`

---

## Quickstart (Local Python)

### Prereqs
- Python 3.11+
- PostgreSQL 16+ running locally

### Setup

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Edit `.env` and set:
- `DATABASE_URL=postgresql+psycopg://<user>:<pass>@localhost:5432/<db>`

### Migrate + Seed

```bash
alembic upgrade head
python -m scripts.seed_db
```

### Run API

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## API Endpoints

### `POST /chat/ask`

Request:

```json
{
  "question": "Show revenue trend for the last 30 days",
  "context": {}
}
```

Response (shape):

```json
{
  "question": "...",
  "answer_text": "...",
  "chart_type": "line",
  "chart_title": "...",
  "kpis": { "values": { "total_revenue": 12345.67 } },
  "filters_detected": { "date_range": "last_n_days", "n_days": 30, "filters": [] },
  "columns": ["date", "revenue"],
  "data": [{ "date": "2026-01-01", "revenue": 1000.0 }],
  "generated_sql": "SELECT ...",
  "confidence": 0.75,
  "warnings": [],
  "powerbi": {
    "visual": {
      "visual": "line",
      "encoding": { "x": "date", "y": "revenue" }
    }
  }
}
```

### `GET /schema`
Returns the semantic layer (metrics/dimensions/tables) for UI or Power BI clients.

### `POST /admin/refresh-semantic-layer`
Reloads `config/semantic_layer.yml` without restarting the server.

### `POST /dev/run-sql` (dev only)
Executes **read-only** SQL with basic safety checks. Disabled when `APP_ENV` is not `dev`/`local`.

---

## Sample Questions to Try

- Show total revenue
- Show revenue trend for the last 30 days
- Top 5 products by profit
- Compare this month revenue with previous month
- Show sales by city
- Which category has the lowest profit?
- Show total orders in Tashkent
- Show top 10 cities by revenue in the last 7 days

---

## Power BI Integration (practical + honest)

Power BI has limitations around interactive “chat” UX inside a report. Common integration approaches:

- **Power Query (Web connector)**:
  - Use **Get Data → Web**
  - Call `POST /chat/ask` via a parameterized query (question as parameter)
  - Best for “refresh-based” scenarios (not real-time chat)
- **Python intermediary / Fabric notebook**:
  - Use a small Python script/notebook to call the API and materialize a table
  - Great when you want more control over auth/caching and shaping the dataset
- **Custom frontend + Embedded Power BI**:
  - Best for real chat UI: build a small web app that calls `/chat/ask` and then drives embedded visuals.

### How to use the response in Power BI

- **Dataset**: use `columns` + `data` to build a table in Power Query.
- **Visual selection**: use `chart_type` or `powerbi.visual.visual`.
- **Axis mapping**: use `powerbi.visual.encoding` keys:
  - line: `x`, `y`
  - bar/column: `category`, `value`
  - kpi: `value`
- **Narrative**: show `answer_text` in a card/text box.
- **Metadata**: use `filters_detected` to display which filters were inferred.

---

## What you’ll edit for your real business data

1. **Database schema**
   - Replace the sample star schema with your own (tables + relationships)
2. **Semantic layer**
   - Update `config/semantic_layer.yml`:
     - add metrics (approved aggregations)
     - add dimensions (approved group-by fields)
     - add named filters (common business filters)
3. **Seed data**
   - Replace `scripts/seed_db.py` with your real ingestion/ELT pipeline

---

## Safety Model (important)

- The chatbot does **not** run LLM-generated SQL.
- SQL is built from **whitelisted** metrics/dimensions using SQLAlchemy.
- `POST /dev/run-sql` is explicitly dev-only and still enforces read-only checks.

---

## Next Improvements (roadmap)

- Better NLP: entity resolution (city/product fuzzy match against DB)
- “Previous period” comparison queries (two queries + delta KPIs)
- Caching layer (Redis) + result fingerprints
- Row-level security / tenant isolation
- Auth (API keys/JWT) for Power BI gateway usage
- Add a small UI or Power BI custom visual for chat input

