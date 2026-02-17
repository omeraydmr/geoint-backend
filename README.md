# STRATYON Backend

**Version:** 2.0.0
**Framework:** Python 3.13+, FastAPI
**Database:** PostgreSQL 16 + PostGIS 3.4
**Market:** Turkiye

---

## Overview

The STRATYON Backend is the API and intelligence engine for the STRATYON Strategic Intelligence Platform. It powers geographic intelligence (GEOINT), AI strategy generation, competitor tracking, Turkish NLP analysis, and media monitoring -- all designed for the Turkish market.

## Prerequisites

- Python 3.13+ (managed via [uv](https://docs.astral.sh/uv/) recommended)
- PostgreSQL 16+ with PostGIS 3.4+ extension
- Redis 7+
- Docker and Docker Compose (recommended for infrastructure)

## Quick Start

### Option 1: Docker Compose (Recommended)

```bash
# Copy environment file
cp .env.example .env
# Edit .env with your API keys and database credentials

# Start all services (PostgreSQL, Redis, Backend)
docker-compose up -d

# Access API docs
open http://localhost:8000/docs
```

### Option 2: Local Development

```bash
# Install uv (if not installed)
# macOS/Linux: curl -LsSf https://astral.sh/uv/install.sh | sh
# Windows: powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Create virtual environment and install dependencies
uv sync

# Or with pip
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Copy environment file
cp .env.example .env
# Edit .env with your values

# Start the application
uvicorn app.main:app --reload --port 8000
```

## API Endpoints

### Core

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/docs` | OpenAPI documentation |

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | Register new user |
| POST | `/api/v1/auth/login` | Login, returns JWT tokens |
| POST | `/api/v1/auth/refresh` | Refresh access token |

### GEOINT (Geographic Intelligence)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/geoint/heatmap/{keyword_id}` | GeoJSON heatmap data |
| GET | `/api/v1/geoint/top-regions/{keyword_id}` | Top regions by GEOINT score |
| POST | `/api/v1/geoint/budget-recommendation` | AI budget allocation |

### Competitors

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/competitors` | List tracked competitors |
| POST | `/api/v1/competitors` | Add competitor |
| GET | `/api/v1/competitors/{id}/gap` | Keyword gap analysis |

### Strategies

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/strategies` | List strategies |
| POST | `/api/v1/strategies` | Create AI strategy |
| GET | `/api/v1/strategies/{id}` | Strategy details |

## Technology Stack

| Category | Technology |
|----------|------------|
| Framework | FastAPI |
| Database | PostgreSQL 16 + PostGIS 3.4 |
| ORM | SQLAlchemy 2.0 (async) |
| Cache | Redis 7 |
| Scheduler | APScheduler |
| AI/ML | OpenAI, Anthropic, LangChain, scikit-learn |
| Geospatial | GeoPandas, Shapely, GeoAlchemy2 |
| NLP | Zemberek (Turkish morphology) |
| Auth | JWT (python-jose), bcrypt |
| Ads APIs | Google Ads, Meta (Facebook) Ads |
| SEO | DataForSEO |

## Project Structure

```
app/
  api/v1/endpoints/   # FastAPI route handlers
  core/               # Config, database, security, caching
  models/             # SQLAlchemy ORM models
  schemas/            # Pydantic request/response schemas
  services/           # Business logic
    ai/               # AI chatbot and insights
    external/         # Google Ads, Meta Ads, TKGM, DataForSEO
    geoint/           # Geographic intelligence engine
    nlp/              # Turkish NLP (Zemberek)
    strategy/         # AI strategy generator
    trends/           # Google Trends integration
  tasks/              # Background tasks (APScheduler)
  middleware/         # Logging, error handling
  websocket/          # Real-time WebSocket events
database/
  schema/             # SQL schema files (001-005)
  init_db.py          # Database initialization script
scripts/              # Seed scripts for geographic data
data/                 # GeoJSON boundary files (Turkey ADM1/ADM2)
docs/                 # Backend-specific documentation
```

## Database

The database uses SQL files as the source of truth. Schema files are in `database/schema/` and are numbered for execution order:

```bash
# Initialize database manually
psql -d stratyon_db -f database/schema/001_initial_schema.sql
psql -d stratyon_db -f database/schema/002_spatial_indexes.sql
psql -d stratyon_db -f database/schema/003_constraints.sql
psql -d stratyon_db -f database/schema/004_competitor_enhancements.sql
psql -d stratyon_db -f database/schema/005_comparison_history.sql

# Seed geographic data
python scripts/seed_turkey_provinces.py
```

## Environment Variables

See `.env.example` for the complete list. Key variables:

| Variable | Required | Description |
|----------|----------|-------------|
| `POSTGRES_*` | Yes | Database connection |
| `REDIS_URL` | Yes | Redis cache URL |
| `JWT_SECRET_KEY` | Yes | JWT signing secret |
| `OPENAI_API_KEY` | No | OpenAI API key (for AI features) |
| `ANTHROPIC_API_KEY` | No | Anthropic API key (for AI features) |
| `DATAFORSEO_LOGIN` | No | DataForSEO credentials |
| `GOOGLE_ADS_*` | No | Google Ads API credentials |
| `META_*` | No | Meta/Facebook Ads credentials |
| `MAPBOX_ACCESS_TOKEN` | No | Mapbox token |

## Testing

```bash
pytest
pytest --cov=app
```

## WebSocket

Real-time updates available at `ws://localhost:8000/ws/{access_token}`. Events include GEOINT updates, competitor changes, and task notifications.

## Rate Limiting

Plan-based rate limits are enforced on all endpoints:
- Free: 50 req/hour
- Insight: 100 req/hour
- Strategy: 500 req/hour
- Growth: 1000 req/hour
- Enterprise: Unlimited

## Related

- **Frontend Repository:** The STRATYON Frontend consumes this API.

---

**STRATYON** - Veriyi Stratejiye Donusturen Guc
