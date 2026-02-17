# STRATYON Microservices Architecture

## 🏗️ Architecture Overview

STRATYON uses a microservices architecture with two primary services:

1. **Java/Spring Boot Service** (Port 8080) - Enterprise backend for business logic, CRUD, and data management
2. **Python/FastAPI Service** (Port 8000) - AI/ML operations, NLP, and LLM integration

```
┌─────────────────────────────────────────────────────────────────┐
│                   Frontend (Next.js - Port 3000)                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│            Nginx API Gateway (Port 80/443)                       │
│  Routes:                                                         │
│  /api/v1/auth/*        → Java Service (8080)                     │
│  /api/v1/keywords/*    → Java Service (8080)                     │
│  /api/v1/strategies/*  → Java Service (8080)                     │
│  /api/v1/ai/*          → Python Service (8000)                   │
│  /api/v1/nlp/*         → Python Service (8000)                   │
└─────────────────────────────────────────────────────────────────┘
        ↓                                       ↓
┌──────────────────────┐              ┌──────────────────────┐
│  Java Spring Boot    │              │  Python FastAPI      │
│  Service (8080)      │◄────REST────►│  AI Service (8000)   │
├──────────────────────┤              ├──────────────────────┤
│ • Authentication     │              │ • AI Strategy Gen    │
│ • User Management    │              │ • Turkish NLP        │
│ • Keywords CRUD      │              │ • Sentiment Analysis │
│ • GEOINT CRUD        │              │ • LLM Orchestration  │
│ • Strategy CRUD      │              │ • OpenAI Integration │
│ • Competitors CRUD   │              │ • Anthropic Claude   │
│ • Media CRUD         │              │ • Google Ads API     │
│ • Data Validation    │              │ • Meta Ads API       │
│ • Caching (Redis)    │              │ • DataForSEO API     │
│ • Transactions       │              │ • ML Model Inference │
└──────────────────────┘              └──────────────────────┘
        ↓                                       ↓
┌──────────────────────┐              ┌──────────────────────┐
│  PostgreSQL + PostGIS│              │    Redis Cache       │
│  (Port 5432)         │              │    (Port 6379)       │
└──────────────────────┘              └──────────────────────┘
```

## 📦 Service Responsibilities

### Java/Spring Boot Service
**Purpose:** Traditional enterprise backend operations

**Responsibilities:**
- ✅ User authentication (Spring Security + JWT)
- ✅ User registration and profile management
- ✅ CRUD operations for all domain entities
- ✅ Database transaction management
- ✅ Data validation and business rules
- ✅ Caching strategies (Redis)
- ✅ API rate limiting
- ✅ Request logging and monitoring
- ✅ Database migrations (Flyway)

**Technology Stack:**
- Java 17
- Spring Boot 3.2.1
- Spring Security 6
- Spring Data JPA + Hibernate
- PostgreSQL + Hibernate Spatial
- Redis for caching
- JWT for authentication
- MapStruct for DTO mapping
- Lombok for boilerplate reduction
- SpringDoc OpenAPI for documentation

### Python/FastAPI Service
**Purpose:** AI/ML operations and external integrations

**Responsibilities:**
- ✅ AI strategy generation (OpenAI GPT-4o-mini, Anthropic Claude)
- ✅ Turkish NLP analysis (morphological, intent detection)
- ✅ Sentiment analysis for media mentions
- ✅ ML model inference
- ✅ LLM prompt management and caching
- ✅ External API integrations:
  - Google Ads API (keyword metrics, ad performance)
  - Meta Ads API (audience insights, ad data)
  - DataForSEO (SEO metrics, competitor analysis)
  - Google Trends (pytrends)
- ✅ GEOINT score calculations
- ✅ Async operations (Celery)

**Technology Stack:**
- Python 3.11+
- FastAPI
- SQLAlchemy (async) - Read-only access
- OpenAI SDK
- Anthropic SDK
- google-ads
- facebook-business
- Redis for LLM caching
- Celery for async tasks
- Pydantic for validation

## 🔐 Authentication Flow

```
1. User Login (Frontend)
   ↓
2. POST /api/v1/auth/login → Java Service
   ↓
3. Java validates credentials (Spring Security)
   ↓
4. Java generates JWT token
   ↓
5. Frontend receives JWT
   ↓
6. All subsequent requests include:
   Header: Authorization: Bearer <JWT>
   ↓
7. Nginx passes JWT to both Java and Python services
   ↓
8. Each service validates JWT independently
```

### JWT Token Structure
```json
{
  "sub": "user@example.com",
  "iat": 1234567890,
  "exp": 1234654290
}
```

## 🔄 Inter-Service Communication

### Java → Python (REST API)

**Use Case:** Java service needs AI operations

```java
// Example: Generate AI strategy
@Service
public class StrategyService {
    @Autowired
    private PythonAIClient pythonClient;

    public Strategy generateStrategy(StrategyRequest request) {
        // Call Python AI service
        AIStrategyResponse aiResponse = pythonClient.generateStrategy(request);

        // Save to database (Java handles persistence)
        Strategy strategy = mapToEntity(aiResponse);
        return strategyRepository.save(strategy);
    }
}
```

### Python → Java (REST API)

**Use Case:** Python service needs user data or to store results

```python
# Example: Get user keywords for AI processing
async def generate_strategy(user_id: str):
    # Call Java service to get user keywords
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{JAVA_SERVICE_URL}/api/v1/keywords",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        keywords = response.json()

    # Process with LLM
    strategy = await llm_service.generate(keywords)

    # Call Java service to save
    await client.post(
        f"{JAVA_SERVICE_URL}/api/v1/strategies",
        json=strategy,
        headers={"Authorization": f"Bearer {jwt_token}"}
    )
```

## 🐳 Docker Compose Configuration

See `docker-compose.microservices.yml` for full configuration.

### Services:
- **nginx** - API Gateway (Port 80/443)
- **java-backend** - Spring Boot Service (Port 8080)
- **python-ai** - FastAPI AI Service (Port 8000)
- **postgres** - PostgreSQL + PostGIS (Port 5432)
- **redis** - Redis Cache (Port 6379)
- **celery-worker** - Celery async worker
- **celery-beat** - Celery scheduler

## 📂 Project Structure

```
geoint/
├── java-services/                    # Java/Spring Boot Service
│   ├── src/main/java/com/stratyon/
│   │   ├── StratyonApplication.java
│   │   ├── config/
│   │   │   ├── SecurityConfig.java
│   │   │   ├── JwtConfig.java
│   │   │   ├── CorsConfig.java
│   │   │   └── RedisConfig.java
│   │   ├── controller/
│   │   │   ├── AuthController.java
│   │   │   ├── KeywordController.java
│   │   │   ├── GeointController.java
│   │   │   ├── StrategyController.java
│   │   │   ├── CompetitorController.java
│   │   │   └── MediaController.java
│   │   ├── service/
│   │   │   ├── AuthService.java
│   │   │   ├── KeywordService.java
│   │   │   ├── GeointService.java
│   │   │   ├── StrategyService.java
│   │   │   └── PythonAIClient.java
│   │   ├── repository/
│   │   │   ├── UserRepository.java
│   │   │   ├── KeywordRepository.java
│   │   │   └── ...
│   │   ├── model/
│   │   │   ├── User.java
│   │   │   ├── Keyword.java
│   │   │   └── ...
│   │   ├── dto/
│   │   │   ├── request/
│   │   │   └── response/
│   │   ├── security/
│   │   │   ├── JwtTokenProvider.java
│   │   │   ├── JwtAuthenticationFilter.java
│   │   │   └── UserDetailsServiceImpl.java
│   │   └── exception/
│   │       └── GlobalExceptionHandler.java
│   ├── src/main/resources/
│   │   ├── application.yml
│   │   ├── application-dev.yml
│   │   ├── application-prod.yml
│   │   └── db/migration/   # Flyway migrations
│   ├── pom.xml
│   └── Dockerfile
│
├── backend/                          # Python/FastAPI AI Service
│   ├── app/
│   │   ├── main.py
│   │   ├── api/v1/endpoints/
│   │   │   ├── ai_strategy.py     # AI strategy generation
│   │   │   ├── nlp.py             # Turkish NLP
│   │   │   └── ml_inference.py    # ML models
│   │   ├── services/
│   │   │   ├── llm/
│   │   │   │   ├── openai_service.py
│   │   │   │   ├── anthropic_service.py
│   │   │   │   └── prompt_manager.py
│   │   │   ├── nlp/
│   │   │   │   └── turkish_analyzer.py
│   │   │   ├── external/
│   │   │   │   ├── google_ads.py
│   │   │   │   ├── meta_ads.py
│   │   │   │   └── dataforseo.py
│   │   │   └── ml/
│   │   │       └── model_inference.py
│   │   ├── core/
│   │   │   ├── java_client.py     # HTTP client for Java service
│   │   │   └── cache.py           # LLM response caching
│   │   └── schemas/
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/                         # Next.js Frontend
│   └── ...
│
├── nginx/
│   ├── nginx.conf                    # API Gateway configuration
│   └── Dockerfile
│
├── docker-compose.microservices.yml
└── MICROSERVICES_ARCHITECTURE.md (this file)
```

## 🚀 Getting Started

### 1. Start All Services
```bash
docker-compose -f docker-compose.microservices.yml up -d
```

### 2. Check Service Health
```bash
# Java service
curl http://localhost:8080/actuator/health

# Python service
curl http://localhost:8000/health

# Via API Gateway
curl http://localhost/api/v1/health
```

### 3. Access Documentation
- **Java API Docs:** http://localhost:8080/swagger-ui.html
- **Python API Docs:** http://localhost:8000/docs
- **Nginx Gateway:** http://localhost/

## 📡 API Gateway Routing

### Nginx Configuration

```nginx
# Java Service Routes
location /api/v1/auth {
    proxy_pass http://java-backend:8080;
}

location /api/v1/keywords {
    proxy_pass http://java-backend:8080;
}

location /api/v1/strategies {
    proxy_pass http://java-backend:8080;
}

# Python Service Routes (AI/ML)
location /api/v1/ai {
    proxy_pass http://python-ai:8000;
}

location /api/v1/nlp {
    proxy_pass http://python-ai:8000;
}

location /api/v1/ml {
    proxy_pass http://python-ai:8000;
}
```

## 🔧 Environment Variables

### Java Service (.env)
```properties
# Database
DB_HOST=postgres
DB_PORT=5432
DB_NAME=stratyon_db
DB_USER=postgres
DB_PASSWORD=your_password

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# JWT
JWT_SECRET=your-256-bit-secret-key

# Python AI Service
PYTHON_AI_SERVICE_URL=http://python-ai:8000

# CORS
CORS_ORIGINS=http://localhost:3000
```

### Python Service (.env)
```properties
# Database (Read-only)
DATABASE_URL=postgresql+asyncpg://postgres:password@postgres:5432/stratyon_db

# Redis
REDIS_URL=redis://redis:6379

# AI/LLM
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# External APIs
GOOGLE_ADS_DEVELOPER_TOKEN=...
META_ACCESS_TOKEN=...
DATAFORSEO_LOGIN=...

# Java Service
JAVA_SERVICE_URL=http://java-backend:8080
```

## 🔐 Security Considerations

1. **JWT Validation:** Both services independently validate JWTs
2. **CORS:** Configured in both Nginx and Spring Boot
3. **Rate Limiting:** Implemented in Java service using Bucket4j
4. **API Keys:** Stored in environment variables, never in code
5. **HTTPS:** Nginx handles SSL termination in production
6. **Database:** Java has full access, Python has read-only access

## 📊 Monitoring & Observability

### Health Checks
- Java: `/actuator/health`
- Python: `/health`
- Database: Automated health checks in Docker Compose

### Metrics
- Java: Prometheus metrics at `/actuator/prometheus`
- Python: Custom metrics endpoint at `/metrics`

### Logging
- Java: Logback with structured logging
- Python: Structlog with JSON output
- Centralized: All logs to stdout, collected by Docker

## 🔄 Development Workflow

### Local Development

**Java Service:**
```bash
cd java-services
mvn spring-boot:run
```

**Python Service:**
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

### Production Deployment

```bash
# Build and deploy all services
docker-compose -f docker-compose.microservices.yml up -d --build

# Scale services
docker-compose -f docker-compose.microservices.yml up -d --scale python-ai=3

# View logs
docker-compose logs -f java-backend
docker-compose logs -f python-ai
```

## 🎯 Migration Strategy

### Phase 1: Parallel Run (Current)
- Both Java and Python services run simultaneously
- Java handles CRUD, Python handles AI/ML
- Nginx routes requests to appropriate service

### Phase 2: Full Microservices (Future)
- Add more specialized microservices:
  - Media Monitoring Service
  - GEOINT Processing Service
  - Analytics Service
- Add service mesh (Istio/Linkerd)
- Add distributed tracing (Jaeger)

## 📚 Additional Resources

- Spring Boot Microservices: https://spring.io/microservices
- FastAPI Best Practices: https://fastapi.tiangolo.com/deployment/
- Nginx Reverse Proxy: https://docs.nginx.com/nginx/admin-guide/web-server/reverse-proxy/
- Docker Compose Networking: https://docs.docker.com/compose/networking/
