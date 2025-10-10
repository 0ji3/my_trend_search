# Development Workflow Guide

## Environment Setup

### Prerequisites
- Docker Desktop installed
- Docker Compose v2+
- Git

### Initial Setup

1. **Clone repository**
```bash
git clone <repository-url>
cd my_trend_search
```

2. **Create environment file**
```bash
cp .env.example .env
```

3. **Required environment variables** (`.env`):
```env
# Database
DATABASE_URL=postgresql://ebayuser:your_secure_password@postgres:5432/ebay_trends
DATABASE_PASSWORD=your_secure_password

# JWT Authentication
SECRET_KEY=your-secret-key-min-32-chars-for-hs256
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440  # 24 hours
REFRESH_TOKEN_EXPIRE_DAYS=30

# Encryption (for OAuth tokens)
ENCRYPTION_KEY=base64-encoded-32-byte-key

# eBay API Credentials
EBAY_CLIENT_ID=your_ebay_app_client_id
EBAY_CLIENT_SECRET=your_ebay_app_secret
EBAY_REDIRECT_URI=http://localhost:3000/oauth/callback
EBAY_ENVIRONMENT=sandbox  # or 'production'

# Redis
REDIS_URL=redis://redis:6379/0

# CORS
CORS_ORIGINS=["http://localhost:3000"]
```

4. **Start services**
```bash
docker-compose up -d
```

5. **Verify services are running**
```bash
docker-compose ps
```

Expected output:
- postgres (port 5432)
- redis (port 6379)
- backend (port 8000)
- frontend (port 3000)
- celery-worker
- celery-beat (when implemented)

---

## Docker Commands

### Start all services
```bash
docker-compose up -d
```

### Stop all services
```bash
docker-compose down
```

### View logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f postgres
docker-compose logs -f celery-worker
```

### Restart specific service
```bash
docker-compose restart backend
docker-compose restart frontend
```

### Rebuild after code changes
```bash
# Backend
docker-compose up -d --build backend

# Frontend
docker-compose up -d --build frontend

# All services
docker-compose up -d --build
```

### Execute commands in containers
```bash
# Backend shell
docker-compose exec backend bash

# Database CLI
docker-compose exec postgres psql -U ebayuser -d ebay_trends

# Redis CLI
docker-compose exec redis redis-cli
```

---

## Database Management

### Alembic Migrations

#### Create new migration
```bash
docker-compose exec backend alembic revision --autogenerate -m "description"
```

#### Apply migrations
```bash
docker-compose exec backend alembic upgrade head
```

#### Check current version
```bash
docker-compose exec backend alembic current
```

#### Downgrade migration
```bash
docker-compose exec backend alembic downgrade -1
```

#### View migration history
```bash
docker-compose exec backend alembic history
```

### Manual Database Operations

#### Connect to PostgreSQL
```bash
docker-compose exec postgres psql -U ebayuser -d ebay_trends
```

#### Common SQL queries
```sql
-- List all tables
\dt

-- Describe table structure
\d tenants
\d oauth_credentials
\d ebay_accounts

-- View data
SELECT * FROM tenants;
SELECT * FROM oauth_credentials;
SELECT * FROM ebay_accounts;

-- Count records
SELECT COUNT(*) FROM tenants;
```

#### Reset database (DANGER!)
```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U ebayuser -d ebay_trends

# Inside psql
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO ebayuser;
GRANT ALL ON SCHEMA public TO public;

# Exit psql
\q

# Re-run migrations
docker-compose exec backend alembic upgrade head
```

---

## Backend Development

### File Structure
```
backend/
├── app/
│   ├── main.py              # FastAPI app entry
│   ├── config.py            # Settings from env vars
│   ├── database.py          # SQLAlchemy session
│   ├── models/              # Database models
│   ├── schemas/             # Pydantic schemas
│   ├── api/                 # API endpoints
│   ├── services/            # Business logic
│   ├── utils/               # Utilities (security, encryption)
│   ├── clients/             # External API clients
│   └── tasks/               # Celery tasks
├── alembic/                 # DB migrations
├── tests/                   # Unit/integration tests
├── requirements.txt         # Python dependencies
└── Dockerfile
```

### Running backend locally (without Docker)
```bash
cd backend

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Set environment variables (create .env in backend/)
export DATABASE_URL=postgresql://ebayuser:password@localhost:5432/ebay_trends
export SECRET_KEY=your-secret-key
# ... etc

# Run server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Testing backend
```bash
# Run all tests
docker-compose exec backend pytest

# Run with coverage
docker-compose exec backend pytest --cov=app --cov-report=html

# Run specific test file
docker-compose exec backend pytest tests/test_auth.py

# Run with verbose output
docker-compose exec backend pytest -v
```

### API Documentation
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI JSON: http://localhost:8000/openapi.json

---

## Frontend Development

### File Structure
```
frontend/
├── public/
├── src/
│   ├── components/          # Reusable components
│   ├── pages/              # Route pages
│   ├── services/           # API clients
│   ├── store/              # Redux store
│   ├── theme/              # MUI theme
│   ├── types/              # TypeScript types
│   ├── App.tsx
│   └── index.tsx
├── package.json
├── tsconfig.json
└── Dockerfile
```

### Running frontend locally (without Docker)
```bash
cd frontend

# Install dependencies
npm install

# Set environment variable
export REACT_APP_API_URL=http://localhost:8000/api

# Run dev server
npm start

# Build for production
npm run build
```

### Frontend testing
```bash
# Run tests
docker-compose exec frontend npm test

# Run linter
docker-compose exec frontend npm run lint

# Type check
docker-compose exec frontend npm run type-check
```

---

## Git Workflow

### Branch Strategy
- `main` - Production-ready code
- `develop` - Integration branch (not yet created)
- `feature/*` - Feature branches
- `fix/*` - Bug fix branches

### Commit Convention
Follow conventional commits format:
```
<type>: <description>

[optional body]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting)
- `refactor`: Code refactoring
- `test`: Adding tests
- `chore`: Build/tooling changes

Examples:
```bash
git commit -m "feat: implement eBay OAuth integration"
git commit -m "fix: resolve token encryption issue"
git commit -m "docs: update API documentation"
```

### Current Commits
```
67984ae - fix
7a5fef3 - Initial commit
```

---

## Celery Background Tasks

### Start Celery worker (standalone)
```bash
docker-compose exec backend celery -A app.celery_app worker --loglevel=info
```

### Start Celery beat scheduler (standalone)
```bash
docker-compose exec backend celery -A app.celery_app beat --loglevel=info
```

### Monitor tasks
```bash
# Celery flower (web UI monitoring)
docker-compose exec backend celery -A app.celery_app flower
# Access at http://localhost:5555
```

### Task debugging
```bash
# Check Redis queue
docker-compose exec redis redis-cli
> KEYS *
> LLEN celery
```

---

## Common Issues and Solutions

### Issue: Port already in use
**Error**: `Bind for 0.0.0.0:8000 failed: port is already allocated`

**Solution**:
```bash
# Find process using port
lsof -i :8000  # Mac/Linux
netstat -ano | findstr :8000  # Windows

# Kill process or change port in docker-compose.yml
```

---

### Issue: Database connection refused
**Error**: `psycopg2.OperationalError: could not connect to server`

**Solution**:
```bash
# Check if postgres is running
docker-compose ps postgres

# Restart postgres
docker-compose restart postgres

# Check logs
docker-compose logs postgres
```

---

### Issue: Alembic empty migration
**Problem**: `alembic revision --autogenerate` creates migration with only `pass` statements

**Solution**:
1. Verify models are imported in `alembic/env.py`:
```python
from app.models import Tenant, OAuthCredential, EbayAccount
```

2. Regenerate migration:
```bash
docker-compose exec backend alembic revision --autogenerate -m "description"
```

---

### Issue: Frontend can't connect to backend
**Error**: `Network Error` or `CORS error`

**Solution**:
1. Check backend is running: `docker-compose ps backend`
2. Verify CORS_ORIGINS in `.env` includes `http://localhost:3000`
3. Check backend logs: `docker-compose logs backend`
4. Verify API URL in frontend: `REACT_APP_API_URL=http://localhost:8000/api`

---

### Issue: Token encryption error
**Error**: `cryptography.exceptions.InvalidTag`

**Solution**:
- ENCRYPTION_KEY changed between encryption and decryption
- Regenerate ENCRYPTION_KEY and re-authorize eBay OAuth:
```bash
python3 -c "import os, base64; print(base64.b64encode(os.urandom(32)).decode())"
```

---

## Testing Workflow

### Manual Testing Checklist

#### Phase 2 (Authentication)
- [ ] Register new user at http://localhost:3000/register
- [ ] Login with created user at http://localhost:3000/login
- [ ] Verify redirect to dashboard after login
- [ ] Verify logout clears tokens and redirects to login
- [ ] Verify protected route redirects to login when not authenticated
- [ ] Verify token auto-refresh on 401 error

#### Phase 3 (eBay OAuth)
- [ ] Click "Connect eBay Account" button
- [ ] Verify redirect to eBay authorization page
- [ ] Complete authorization on eBay sandbox
- [ ] Verify redirect to /oauth/callback
- [ ] Verify success message and redirect to dashboard
- [ ] Verify eBay connection status shows "Connected"
- [ ] Verify token expiration displays correctly
- [ ] Verify "Disconnect OAuth" removes credentials

### Automated Testing
```bash
# Backend unit tests
docker-compose exec backend pytest tests/

# Frontend component tests
docker-compose exec frontend npm test

# Integration tests (future)
docker-compose exec backend pytest tests/integration/
```

---

## Production Deployment (Future)

### Environment Differences
- Use production eBay API credentials
- Change EBAY_ENVIRONMENT to 'production'
- Use strong SECRET_KEY and ENCRYPTION_KEY
- Enable HTTPS
- Configure proper CORS_ORIGINS
- Use managed PostgreSQL and Redis
- Set up monitoring and logging
- Configure backup strategy

### Docker Compose Production Overrides
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

---

## Development Phases Progress

### ✅ Phase 1: Infrastructure (Completed)
- Docker environment
- PostgreSQL + Redis
- FastAPI skeleton
- React skeleton
- Basic database schema

### ✅ Phase 2: Authentication (Completed)
- User registration/login
- JWT tokens
- Password hashing
- Frontend auth forms
- Protected routes
- Token auto-refresh

### ✅ Phase 3: eBay OAuth (Completed)
- OAuth 2.0 flow
- Token encryption (AES-256-GCM)
- Token storage
- Frontend OAuth UI
- Callback handling
- Account management

### 🔜 Phase 4: Data Synchronization (Next)
- Trading API client
- Listing data fetch
- Daily metrics collection
- Celery tasks
- Manual sync trigger

### 🔜 Phase 5: Trend Analysis
### 🔜 Phase 6: Dashboard & Visualization
### 🔜 Phase 7: Additional Features
### 🔜 Phase 8: Testing & Optimization

---

## Useful Commands Reference

```bash
# Docker
docker-compose up -d               # Start all services
docker-compose down                # Stop all services
docker-compose logs -f backend     # View backend logs
docker-compose restart backend     # Restart backend
docker-compose exec backend bash   # Enter backend shell

# Database
docker-compose exec postgres psql -U ebayuser -d ebay_trends
docker-compose exec backend alembic upgrade head
docker-compose exec backend alembic revision --autogenerate -m "msg"

# Backend
docker-compose exec backend pytest
docker-compose exec backend python -m app.main

# Frontend
docker-compose exec frontend npm install
docker-compose exec frontend npm start
docker-compose exec frontend npm test

# Redis
docker-compose exec redis redis-cli
docker-compose exec redis redis-cli KEYS '*'

# Celery
docker-compose exec backend celery -A app.celery_app worker --loglevel=info
docker-compose exec backend celery -A app.celery_app beat --loglevel=info
```
