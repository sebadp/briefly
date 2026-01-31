# Briefly Backend

FastAPI backend for the Briefly news feed application.

## Quick Start

```bash
# 1. Start databases
docker-compose up -d

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -e ".[dev]"

# 4. Configure environment
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# 5. Run the server
uvicorn app.main:app --reload
```

Open http://localhost:8000/docs for the API documentation.

## Project Structure

```
backend/
├── app/
│   ├── api/v1/          # API endpoints
│   │   ├── feeds.py     # Feed CRUD
│   │   ├── sources.py   # Source management
│   │   └── articles.py  # Article retrieval
│   ├── schemas/         # Pydantic schemas
│   ├── models/          # SQLModel DB models
│   ├── services/        # Business logic
│   ├── agents/          # Strands AI agents
│   ├── db/              # Database connections
│   ├── config.py        # Settings
│   └── main.py          # FastAPI app
├── tests/
├── docker-compose.yml
└── pyproject.toml
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/api/v1/feeds` | List feeds |
| POST | `/api/v1/feeds` | Create feed |
| POST | `/api/v1/feeds/from-natural-language` | Create feed from NL |
| GET | `/api/v1/feeds/{id}` | Get feed |
| DELETE | `/api/v1/feeds/{id}` | Delete feed |
| GET | `/api/v1/sources` | List sources |
| POST | `/api/v1/sources` | Add source |
| GET | `/api/v1/articles` | List articles |
| POST | `/api/v1/articles/scrape` | Trigger scrape |

## Development

```bash
# Run tests
pytest -v

# Type checking
mypy .

# Linting & formatting
ruff check .
ruff format .
```
