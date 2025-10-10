# eBay Trend Research Tool - Project Structure

## Overview
Multi-tenant SaaS application for eBay sellers to monitor listing performance and identify trending items.

## Technology Stack
- **Backend**: FastAPI (Python 3.11+), SQLAlchemy, Alembic
- **Frontend**: React 18 + TypeScript + Material-UI + Redux Toolkit
- **Database**: PostgreSQL 16
- **Cache/Queue**: Redis 7, Celery
- **Container**: Docker Compose

## Project Directory Structure

```
my_trend_search/
├── backend/
│   ├── alembic/                    # Database migrations
│   │   ├── versions/               # Migration files
│   │   └── env.py                  # Alembic configuration
│   ├── app/
│   │   ├── api/                    # API endpoints
│   │   │   ├── auth.py            # Authentication endpoints
│   │   │   └── ebay_accounts.py   # eBay OAuth & account endpoints
│   │   ├── models/                 # SQLAlchemy models
│   │   │   ├── tenant.py          # User/tenant model
│   │   │   ├── oauth_credential.py # Encrypted OAuth tokens
│   │   │   └── ebay_account.py    # eBay seller accounts
│   │   ├── schemas/                # Pydantic schemas
│   │   │   ├── auth.py            # Auth request/response schemas
│   │   │   └── ebay.py            # eBay OAuth schemas
│   │   ├── services/               # Business logic
│   │   │   ├── auth_service.py    # Authentication service
│   │   │   └── ebay_oauth_service.py # eBay OAuth 2.0 service
│   │   ├── utils/                  # Utilities
│   │   │   ├── security.py        # JWT, password hashing
│   │   │   └── encryption.py      # AES-256-GCM token encryption
│   │   ├── clients/                # External API clients (future)
│   │   ├── tasks/                  # Celery tasks (future)
│   │   ├── config.py              # Configuration management
│   │   ├── database.py            # Database connection
│   │   └── main.py                # FastAPI application entry
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── auth/              # Login/Register forms
│   │   │   ├── common/            # PrivateRoute wrapper
│   │   │   └── ebay/              # EbayConnection component
│   │   ├── pages/
│   │   │   ├── Login.tsx
│   │   │   ├── Register.tsx
│   │   │   ├── Dashboard.tsx
│   │   │   └── OAuthCallback.tsx  # eBay OAuth callback handler
│   │   ├── services/
│   │   │   ├── api.ts             # Axios client with auto-refresh
│   │   │   ├── auth.service.ts    # Authentication API calls
│   │   │   └── ebay.service.ts    # eBay OAuth API calls
│   │   ├── store/                 # Redux state management
│   │   │   ├── store.ts
│   │   │   ├── authSlice.ts
│   │   │   └── hooks.ts
│   │   ├── types/                 # TypeScript interfaces
│   │   ├── theme/                 # MUI theme
│   │   └── App.tsx
│   ├── Dockerfile
│   └── package.json
│
├── database/
│   └── init.sql                   # Initial schema (reference only)
│
├── docker-compose.yml             # Multi-service orchestration
├── .env.example                   # Environment variable template
├── CLAUDE.md                      # Development guide
└── README.md
```

## Completed Phases

### Phase 1: Infrastructure (✅)
- Docker Compose setup (PostgreSQL, Redis, FastAPI, React, Celery)
- Database schema design
- Project skeleton

### Phase 2: Authentication System (✅)
**Backend:**
- Tenant model with bcrypt password hashing
- JWT authentication (access + refresh tokens)
- 6 auth endpoints (register, login, refresh, me, change-password, logout)

**Frontend:**
- Redux Toolkit state management
- Login/Register forms with validation
- PrivateRoute for protected routes
- Dashboard page

### Phase 3: eBay OAuth Integration (✅)
**Backend:**
- OAuthCredential model with AES-256-GCM encryption
- EbayAccount model
- eBay OAuth 2.0 service (authorization, token exchange, auto-refresh)
- 6 eBay endpoints (auth-url, callback, status, list, delete, disconnect)
- Alembic migration with all tables

**Frontend:**
- EbayConnection component with status display
- OAuthCallback page for OAuth redirect handling
- ebay.service.ts for OAuth operations
- CSRF protection with state parameter

## Key Design Patterns

### Backend
- **Multi-tenant architecture**: Row Level Security (RLS) ready
- **Security**: AES-256-GCM for OAuth tokens, bcrypt for passwords, JWT for sessions
- **Service layer**: Separation of business logic from API endpoints
- **Encrypted token storage**: IV + auth tag + ciphertext for OAuth tokens

### Frontend
- **Protected routes**: PrivateRoute wrapper with auto-redirect
- **Auto token refresh**: Axios interceptor for 401 handling
- **State management**: Redux Toolkit with typed hooks
- **Type safety**: Full TypeScript with interfaces

## Database Schema

### Current Tables
1. **tenants**: User accounts (email, password_hash, business_name, timezone, status)
2. **oauth_credentials**: Encrypted eBay OAuth tokens (one-to-one with tenant)
3. **ebay_accounts**: eBay seller account info (one-to-many with oauth_credential)

### Relationships
- Tenant → OAuthCredential (1:1)
- Tenant → EbayAccount (1:N)
- OAuthCredential → EbayAccount (1:N)

## API Endpoints

### Authentication (`/api/auth`)
- POST `/register` - User registration
- POST `/login` - User login
- POST `/refresh` - Token refresh
- GET `/me` - Current user info
- POST `/change-password` - Password change
- POST `/logout` - Logout

### eBay Accounts (`/api/ebay-accounts`)
- GET `/auth-url` - Generate OAuth URL
- POST `/callback` - OAuth callback handler
- GET `/status` - Connection status
- GET `/` - List accounts
- DELETE `/{account_id}` - Delete account
- DELETE `/oauth/disconnect` - Full disconnect

## Environment Variables

### Required
- `DATABASE_URL` - PostgreSQL connection string
- `SECRET_KEY` - JWT signing key (base64, 32+ bytes)
- `ENCRYPTION_KEY` - AES-256 key (base64, 32 bytes)
- `EBAY_CLIENT_ID` - eBay Developer App ID
- `EBAY_CLIENT_SECRET` - eBay Developer Secret
- `EBAY_REDIRECT_URI` - OAuth callback URL (backend)
- `EBAY_ENVIRONMENT` - "sandbox" or "production"

## Next Phases (Planned)

### Phase 4: Data Synchronization
- Trading API client implementation
- Listing data sync (GetMyeBaySelling, GetItem)
- daily_metrics table and Celery tasks
- Manual and scheduled sync

### Phase 5: Trend Analysis
- Trend calculation algorithm (view/watch growth rates)
- TOP10 extraction
- trend_analysis table

### Phase 6: Dashboard & Visualization
- Performance charts (Recharts)
- Trending items list
- KPI cards with real data

### Phase 7: Additional Features
- Notifications
- Analytics API integration
- Feed API for bulk sync
- Reports

## Development Notes
- All services run in Docker containers
- Frontend dev server on port 3000
- Backend API on port 8000
- API docs at http://localhost:8000/docs
- Database migrations via Alembic
