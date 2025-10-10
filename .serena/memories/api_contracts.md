# API Contracts Documentation

## Base URL
- Development: `http://localhost:8000/api`
- Production: TBD

## Authentication

All protected endpoints require `Authorization: Bearer {access_token}` header.

---

## Auth Endpoints (`/api/auth`)

### POST `/auth/register`
**Purpose**: Create new user account

**Request Body**:
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123",
  "business_name": "My eBay Business (optional)",
  "timezone": "America/New_York (optional, default: UTC)"
}
```

**Response** (201 Created):
```json
{
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc...",
  "token_type": "bearer",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "business_name": "My eBay Business",
    "timezone": "America/New_York",
    "status": "active",
    "created_at": "2025-01-10T12:00:00Z"
  }
}
```

**Errors**:
- 400: Email already registered
- 422: Validation error (invalid email format, weak password)

---

### POST `/auth/login`
**Purpose**: Authenticate existing user

**Request Body**:
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123"
}
```

**Response** (200 OK):
```json
{
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc...",
  "token_type": "bearer",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "business_name": "My eBay Business",
    "timezone": "America/New_York",
    "status": "active",
    "created_at": "2025-01-10T12:00:00Z"
  }
}
```

**Errors**:
- 401: Invalid credentials
- 403: Account inactive

---

### POST `/auth/refresh`
**Purpose**: Get new access token using refresh token

**Request Body**:
```json
{
  "refresh_token": "eyJhbGc..."
}
```

**Response** (200 OK):
```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer"
}
```

**Errors**:
- 401: Invalid or expired refresh token

---

### POST `/auth/logout`
**Purpose**: Invalidate refresh token

**Headers**: `Authorization: Bearer {access_token}` (required)

**Response** (200 OK):
```json
{
  "message": "Successfully logged out"
}
```

---

### GET `/auth/me`
**Purpose**: Get current authenticated user info

**Headers**: `Authorization: Bearer {access_token}` (required)

**Response** (200 OK):
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "business_name": "My eBay Business",
  "timezone": "America/New_York",
  "status": "active",
  "created_at": "2025-01-10T12:00:00Z"
}
```

**Errors**:
- 401: Invalid or expired token

---

## eBay Account Endpoints (`/api/ebay-accounts`)

All endpoints require authentication.

### GET `/ebay-accounts/auth-url`
**Purpose**: Generate eBay OAuth authorization URL

**Response** (200 OK):
```json
{
  "authorization_url": "https://auth.ebay.com/oauth2/authorize?client_id=...&redirect_uri=...&response_type=code&scope=...&state=...",
  "state": "random_csrf_token_32_chars"
}
```

**Notes**:
- Client should store `state` in sessionStorage for validation
- Client should redirect user to `authorization_url`

---

### POST `/ebay-accounts/callback`
**Purpose**: Exchange eBay authorization code for tokens

**Request Body**:
```json
{
  "code": "v^1.1#i^1#p^3#...",
  "state": "random_csrf_token_32_chars (optional)"
}
```

**Response** (200 OK):
```json
{
  "message": "eBay account connected successfully",
  "credential_id": "uuid"
}
```

**Side Effects**:
- Creates OAuthCredential record with encrypted tokens
- Creates EbayAccount record(s) based on token's user info
- Tokens are encrypted with AES-256-GCM before storage

**Errors**:
- 400: Invalid authorization code
- 409: User already has OAuth credentials (duplicate connection)
- 500: eBay API communication error

---

### GET `/ebay-accounts/status`
**Purpose**: Get current OAuth connection status

**Response** (200 OK):
```json
{
  "is_connected": true,
  "has_valid_token": true,
  "access_token_expires_at": "2025-01-10T14:00:00Z",
  "accounts_count": 2,
  "accounts": [
    {
      "id": "uuid",
      "tenant_id": "uuid",
      "oauth_credential_id": "uuid",
      "ebay_user_id": "ebay_user_123",
      "username": "my_ebay_store",
      "email": "ebay@example.com",
      "marketplace_id": "EBAY_US",
      "is_active": true,
      "last_sync_at": "2025-01-10T02:00:00Z",
      "created_at": "2025-01-09T10:00:00Z",
      "updated_at": "2025-01-10T02:00:00Z"
    }
  ]
}
```

**When Not Connected**:
```json
{
  "is_connected": false,
  "has_valid_token": false,
  "access_token_expires_at": null,
  "accounts_count": 0,
  "accounts": []
}
```

---

### GET `/ebay-accounts/`
**Purpose**: List all connected eBay accounts

**Query Parameters**:
- `skip` (int, default=0): Pagination offset
- `limit` (int, default=100): Max results

**Response** (200 OK):
```json
{
  "accounts": [
    {
      "id": "uuid",
      "tenant_id": "uuid",
      "oauth_credential_id": "uuid",
      "ebay_user_id": "ebay_user_123",
      "username": "my_ebay_store",
      "email": "ebay@example.com",
      "marketplace_id": "EBAY_US",
      "is_active": true,
      "last_sync_at": "2025-01-10T02:00:00Z",
      "created_at": "2025-01-09T10:00:00Z",
      "updated_at": "2025-01-10T02:00:00Z"
    }
  ],
  "total": 1
}
```

---

### DELETE `/ebay-accounts/{account_id}`
**Purpose**: Delete specific eBay account

**Path Parameters**:
- `account_id` (UUID): Account to delete

**Response** (200 OK):
```json
{
  "message": "eBay account deleted successfully"
}
```

**Side Effects**:
- Deletes EbayAccount record
- Cascades to delete all associated listings, metrics, trends

**Errors**:
- 404: Account not found or belongs to another user

---

### DELETE `/ebay-accounts/oauth/disconnect`
**Purpose**: Disconnect OAuth and delete all credentials/accounts

**Response** (200 OK):
```json
{
  "message": "OAuth disconnected successfully"
}
```

**Side Effects**:
- Deletes OAuthCredential record
- Cascades to delete all EbayAccount records
- Cascades to delete all listings, metrics, trends

**Errors**:
- 404: No OAuth credentials found

---

## Future Endpoints (Not Yet Implemented)

### Listings (`/api/listings`)
- `GET /listings` - List all active listings
- `GET /listings/{listing_id}` - Get listing details
- `GET /listings/{listing_id}/metrics` - Get metrics history

### Trends (`/api/trends`)
- `GET /trends/top10` - Today's top 10 trending items
- `GET /trends/history/{listing_id}` - Trend history for specific listing

### Dashboard (`/api/dashboard`)
- `GET /dashboard/summary` - KPI summary (total listings, accounts, trending count)
- `GET /dashboard/performance` - Performance metrics over time

### Sync (`/api/sync`)
- `POST /sync/trigger` - Manually trigger data sync
- `GET /sync/status/{job_id}` - Check sync job status

---

## Error Response Format

All endpoints return errors in consistent format:

```json
{
  "detail": "Human-readable error message"
}
```

**HTTP Status Codes**:
- 400: Bad Request (invalid input)
- 401: Unauthorized (missing/invalid token)
- 403: Forbidden (account inactive, insufficient permissions)
- 404: Not Found (resource doesn't exist)
- 409: Conflict (duplicate resource)
- 422: Unprocessable Entity (validation error)
- 500: Internal Server Error

**Validation Errors** (422):
```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "value is not a valid email address",
      "type": "value_error.email"
    }
  ]
}
```

---

## Authentication Flow

### Initial Login/Register
1. Client: `POST /auth/register` or `POST /auth/login`
2. Server: Returns `access_token` (24h) + `refresh_token` (30d)
3. Client: Stores both tokens in localStorage
4. Client: Uses `access_token` in `Authorization: Bearer` header

### Token Refresh (when access token expires)
1. Client: Detects 401 response
2. Client: `POST /auth/refresh` with stored `refresh_token`
3. Server: Returns new `access_token`
4. Client: Updates localStorage, retries original request

### eBay OAuth Flow
1. Client: `GET /ebay-accounts/auth-url`
2. Client: Stores `state` in sessionStorage
3. Client: Redirects to `authorization_url` (eBay website)
4. User: Authorizes on eBay
5. eBay: Redirects to `http://localhost:3000/oauth/callback?code=...&state=...`
6. Client: Validates `state` matches sessionStorage
7. Client: `POST /ebay-accounts/callback` with `code` and `state`
8. Server: Exchanges code for tokens, saves encrypted
9. Client: Shows success, redirects to dashboard

---

## Security Notes

- **Passwords**: Never sent in plaintext outside login/register. Hashed with bcrypt (cost 12).
- **JWT Tokens**: HS256 algorithm, 24h expiration for access, 30d for refresh.
- **OAuth Tokens**: Encrypted with AES-256-GCM before database storage.
- **CORS**: Configured to allow `http://localhost:3000` in development.
- **CSRF**: OAuth state parameter provides CSRF protection.
- **Row Level Security**: Database enforces tenant isolation (future enhancement).
