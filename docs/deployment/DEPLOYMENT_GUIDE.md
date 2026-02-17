# Stratyon Platform - Deployment Guide

## Overview

This guide covers deploying all 7 technical improvements to the Stratyon GEO Intelligence Platform.

---

## Prerequisites

### System Requirements
- Python 3.13+
- PostgreSQL 14+ with PostGIS 3.4+
- Redis 7+
- Node.js 18+ (for frontend)
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Docker & Docker Compose (recommended)

### Environment Setup

```bash
# Install uv (if not already installed)
# macOS/Linux:
curl -LsSf https://astral.sh/uv/install.sh | sh
# Windows:
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Backend dependencies
cd backend
uv sync              # Creates .venv and installs all production dependencies
uv sync --extra dev  # Include dev/test dependencies (pytest, etc.)

# Frontend dependencies
cd ../frontend
npm install
```

#### Common uv Commands
```bash
uv add <package>           # Add a new dependency
uv add --dev <package>     # Add a dev dependency
uv remove <package>        # Remove a dependency
uv lock                    # Regenerate lock file after manual pyproject.toml edits
uv sync                    # Install from lock file (reproducible)
uv run <command>           # Run a command in the project's virtualenv
```

---

## Phase 1: Database Setup

### 1.1 Configure PostgreSQL with PostGIS

```bash
# Install PostGIS extension
sudo -u postgres psql stratyon_db
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
\q
```

### 1.2 Set Environment Variables

Create `.env` file in `backend/` directory:

```env
# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=stratyon_db

# Redis
REDIS_URL=redis://localhost:6379/0

# Security
JWT_SECRET_KEY=your_very_secure_secret_key_here
REFRESH_TOKEN_EXPIRE_DAYS=7
MAX_REFRESH_TOKENS_PER_USER=5

# Caching
CACHE_ENABLED=true
CACHE_DEFAULT_TTL=300
CACHE_GEOINT_TTL=900
CACHE_USER_TTL=600

# External APIs (configure as needed)
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
GOOGLE_ADS_DEVELOPER_TOKEN=your_token
# ... other API keys
```

### 1.3 Run Database Migrations

```bash
cd backend

# Initialize Alembic (if not already done)
uv run alembic upgrade head

# This will:
# - Create refresh_tokens table
# - Add spatial GIST indexes to provinces, districts, neighborhoods
```

---

## Phase 2: Deploy Backend

### 2.1 Start Redis

```bash
# Using Docker
docker run -d --name stratyon-redis \
  -p 6379:6379 \
  redis:7-alpine redis-server \
  --appendonly yes \
  --maxmemory 512mb \
  --maxmemory-policy allkeys-lru

# Or using system service
sudo systemctl start redis
```

### 2.2 Start Backend Server

#### Development
```bash
cd backend
uv run uvicorn app.main:app --reload --port 8000
```

#### Production (using Gunicorn)
```bash
cd backend
uv run gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile - \
  --log-level info
```

> **Note:** The platform uses APScheduler for background task scheduling (replacing Celery). Scheduled tasks start automatically with the backend server — no separate worker processes needed.

---

## Phase 3: Verify Deployment

### 3.1 Health Check

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "app": "STRATYON",
  "environment": "production",
  "version": "1.0.0"
}
```

### 3.2 Test Redis Connection

```bash
redis-cli ping
# Should return: PONG

# Check cache stats
redis-cli INFO stats
```

### 3.3 Test Database Connection

```bash
psql -U postgres -d stratyon_db -c "SELECT PostGIS_version();"
```

### 3.4 Check Spatial Indexes

```bash
psql -U postgres -d stratyon_db -c "
SELECT tablename, indexname
FROM pg_indexes
WHERE indexname LIKE '%_gist';
"
```

Should show:
- idx_provinces_geom_gist
- idx_provinces_centroid_gist
- idx_districts_geom_gist
- idx_districts_centroid_gist
- idx_neighborhoods_geom_gist
- idx_neighborhoods_centroid_gist

---

## Phase 4: API Testing

### 4.1 Register User

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePass123",
    "full_name": "Test User"
  }'
```

### 4.2 Login (Get Tokens)

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePass123"
  }'
```

Response includes:
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### 4.3 Test Refresh Token

```bash
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "YOUR_REFRESH_TOKEN"
  }'
```

### 4.4 Test Cached Endpoint

```bash
# First request (cache miss - slower)
time curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  http://localhost:8000/api/v1/geoint/heatmap/KEYWORD_ID

# Second request (cache hit - much faster)
time curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  http://localhost:8000/api/v1/geoint/heatmap/KEYWORD_ID
```

Check response headers:
- `X-Request-ID`: Request correlation ID
- `X-RateLimit-Limit`: Rate limit
- `X-RateLimit-Remaining`: Remaining requests

### 4.5 Test WebSocket

```javascript
// JavaScript client
const token = "YOUR_ACCESS_TOKEN";
const ws = new WebSocket(`ws://localhost:8000/ws/${token}`);

ws.onopen = () => {
  console.log("Connected");
  // Send ping
  ws.send("ping");
};

ws.onmessage = (event) => {
  console.log("Message:", JSON.parse(event.data));
};
```

---

## Phase 5: Monitoring

### 5.1 Check Logs

```bash
# Backend logs (includes APScheduler output)
tail -f logs/stratyon.log
```

### 5.2 Monitor Redis

```bash
# Real-time stats
redis-cli --stat

# Check memory usage
redis-cli INFO memory

# Check cache hit rate
redis-cli INFO stats | grep keyspace
```

### 5.3 Monitor Database

```bash
# Active connections
psql -U postgres -d stratyon_db -c "
SELECT count(*) FROM pg_stat_activity
WHERE datname='stratyon_db';
"

# Slow queries
psql -U postgres -d stratyon_db -c "
SELECT query, calls, total_time, mean_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;
"
```

---

## Phase 6: Performance Optimization

### 6.1 Redis Tuning

Add to `redis.conf`:
```conf
maxmemory 512mb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
```

### 6.2 PostgreSQL Tuning

Add to `postgresql.conf`:
```conf
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
work_mem = 16MB
max_worker_processes = 4
max_parallel_workers_per_gather = 2
max_parallel_workers = 4
```

### 6.3 Application Tuning

```python
# config.py
CACHE_GEOINT_TTL = 900  # 15 min (aggressive)
CACHE_USER_TTL = 600    # 10 min
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7
```

---

## Phase 7: Production Checklist

- [ ] Environment variables configured
- [ ] Database migrations applied
- [ ] Spatial indexes created and verified
- [ ] Redis running and accessible
- [ ] Backend server running (APScheduler starts automatically)
- [ ] Health check passes
- [ ] API authentication working
- [ ] Refresh tokens working
- [ ] Rate limiting functional
- [ ] Caching working (check cache hit rate)
- [ ] WebSocket connections working
- [ ] Logs being written
- [ ] Monitoring configured
- [ ] Backups configured
- [ ] SSL/TLS certificates installed (for production)
- [ ] Firewall rules configured
- [ ] Domain/DNS configured

---

## Phase 8: Docker Deployment (Recommended)

### 8.1 Use Docker Compose

```bash
# Start all services
docker-compose -f docker-compose.microservices.yml up -d

# Check status
docker-compose -f docker-compose.microservices.yml ps

# View logs
docker-compose -f docker-compose.microservices.yml logs -f

# Stop services
docker-compose -f docker-compose.microservices.yml down
```

Services included:
- Nginx (gateway)
- Python AI service (FastAPI + APScheduler)
- Java backend (Spring Boot)
- PostgreSQL + PostGIS
- Redis

---

## Rollback Procedure

### If Issues Occur:

1. **Rollback Database:**
```bash
uv run alembic downgrade -1  # Rollback last migration
uv run alembic downgrade -2  # Rollback two migrations
```

2. **Clear Redis Cache:**
```bash
redis-cli FLUSHDB
```

3. **Disable Caching:**
```env
CACHE_ENABLED=false
```

4. **Restart Services:**
```bash
docker-compose restart
# or
systemctl restart stratyon-api
```

---

## Support

For issues:
1. Check logs: `backend/logs/`
2. Verify configuration: `.env` file
3. Test connections: Redis, PostgreSQL
4. Check GitHub issues: https://github.com/yourusername/stratyon

---

## Success Metrics

After deployment, verify:

**Performance:**
- Heatmap generation: <500ms (was 2-5s)
- Cache hit rate: >80%
- API response time: <200ms

**Security:**
- All tokens expire correctly
- Refresh tokens stored hashed
- Rate limiting prevents abuse

**Reliability:**
- Error rate: <0.1%
- Uptime: >99.9%
- WebSocket reconnection working

---

## Next Steps

1. Configure monitoring (Prometheus, Grafana)
2. Set up alerting (PagerDuty, Slack)
3. Configure automated backups
4. Set up CI/CD pipeline
5. Load testing
6. Security audit
