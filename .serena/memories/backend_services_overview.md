# Backend Services Overview

## Service Layer (backend/app/services/)

### 1. AuthService (`auth_service.py`)

**Purpose**: User authentication and session management

**Class**: `AuthService` (static methods)

**Key Methods**:

1. **`register_tenant(db, tenant_data)`**
   - Validate email uniqueness
   - Hash password with bcrypt
   - Create new tenant record
   - Returns: Tenant object

2. **`authenticate_tenant(db, login_data)`**
   - Verify email exists
   - Check account status (must be 'active')
   - Verify password with bcrypt
   - Returns: Tenant object or None

3. **`create_tokens(tenant)`**
   - Generate JWT access token (24h expiry)
   - Generate JWT refresh token (30d expiry)
   - Returns: TokenResponse with both tokens

4. **`refresh_access_token(db, refresh_token)`**
   - Verify refresh token
   - Check tenant still active
   - Generate new access + refresh tokens
   - Returns: New TokenResponse

5. **`get_current_tenant(db, access_token)`**
   - Verify access token
   - Fetch tenant from database
   - Check active status
   - Returns: Tenant object or None

6. **`change_password(db, tenant, current_password, new_password)`**
   - Verify current password
   - Hash new password
   - Update database
   - Returns: bool

**Security Features**:
- Password strength validation in schema
- bcrypt with auto-truncation for 72-byte limit
- JWT with HS256 algorithm
- Token type validation (access vs refresh)

---

### 2. EbayOAuthService (`ebay_oauth_service.py`)

**Purpose**: eBay OAuth 2.0 flow management and token lifecycle

**Class**: `EbayOAuthService`

**Configuration**:
- Supports sandbox and production environments
- OAuth endpoints auto-selected based on `EBAY_ENVIRONMENT`
- Required scopes:
  - `sell.inventory`
  - `sell.inventory.readonly`
  - `sell.fulfillment`
  - `sell.analytics.readonly`

**Key Methods**:

1. **`generate_authorization_url(state=None)`**
   - Generate OAuth URL with all required scopes
   - Create CSRF state token (if not provided)
   - Returns: (authorization_url, state)

2. **`exchange_code_for_tokens(authorization_code)`**
   - Exchange auth code for tokens via eBay API
   - POST to token endpoint with Basic Auth
   - Returns: dict with access_token, refresh_token, expires_in

3. **`refresh_access_token(refresh_token)`**
   - Request new access token using refresh token
   - Maintains same scopes
   - Returns: dict with new access_token, expires_in

4. **`save_oauth_credentials(db, tenant, access_token, refresh_token, expires_in, refresh_token_expires_in)`**
   - Encrypt tokens with AES-256-GCM
   - Calculate expiration timestamps
   - Create or update OAuthCredential record
   - Returns: OAuthCredential object

5. **`get_valid_access_token(db, tenant)`**
   - Get credential from database
   - Check expiration
   - Auto-refresh if expired
   - Decrypt and return valid token
   - Returns: str (access token) or None

6. **`delete_oauth_credentials(db, tenant)`**
   - Delete OAuth credential (cascades to accounts)
   - Returns: bool

**OAuth Flow**:
```
1. User clicks "Connect eBay"
2. Frontend calls GET /api/ebay-accounts/auth-url
3. Service generates URL with state
4. User redirected to eBay
5. User authorizes app
6. eBay redirects to frontend callback with code
7. Frontend calls POST /api/ebay-accounts/callback
8. Service exchanges code for tokens
9. Tokens encrypted and saved to database
10. Success response to frontend
```

**Token Refresh Flow**:
```
1. API call requires access token
2. Service calls get_valid_access_token()
3. If expired: decrypt refresh token → call eBay API → get new access token
4. Encrypt and update credential
5. Return valid token
```

**Error Handling**:
- Network errors during token exchange
- Invalid authorization codes
- Expired refresh tokens
- eBay API errors

---

## Utility Modules (backend/app/utils/)

### 1. Security Utils (`security.py`)

**Functions**:

1. **`hash_password(password)`**
   - Truncate to 72 bytes if needed (bcrypt limit)
   - Hash with bcrypt
   - Returns: hashed password string

2. **`verify_password(plain_password, hashed_password)`**
   - Verify password against hash
   - Returns: bool

3. **`create_access_token(data, expires_delta=None)`**
   - Create JWT with type='access'
   - Default expiry: 24 hours (from settings)
   - Algorithm: HS256
   - Returns: encoded JWT string

4. **`create_refresh_token(data, expires_delta=None)`**
   - Create JWT with type='refresh'
   - Default expiry: 30 days (from settings)
   - Algorithm: HS256
   - Returns: encoded JWT string

5. **`verify_token(token, token_type='access')`**
   - Decode JWT
   - Verify token type matches
   - Extract tenant_id and email
   - Returns: TokenData object or None

6. **`decode_token(token)`**
   - Decode without verification (debugging)
   - Returns: payload dict or None

**Configuration**:
- Uses `pwd_context` from passlib with bcrypt scheme
- `bcrypt__truncate_error=False` for auto-truncation

---

### 2. Encryption Utils (`encryption.py`)

**Purpose**: AES-256-GCM encryption for OAuth tokens

**Functions**:

1. **`get_encryption_key()`**
   - Load ENCRYPTION_KEY from settings
   - Decode base64
   - Validate 32-byte length
   - Returns: bytes

2. **`encrypt_token(plaintext)`**
   - Generate random 12-byte IV
   - Encrypt with AES-GCM
   - Split ciphertext and 16-byte auth tag
   - Returns: dict {ciphertext, iv, auth_tag}

3. **`decrypt_token(ciphertext, iv, auth_tag)`**
   - Reconstruct ciphertext + tag
   - Decrypt with AES-GCM
   - Verify authentication tag
   - Returns: str (plaintext)

4. **`encrypt_oauth_tokens(access_token, refresh_token)`**
   - Encrypt both tokens separately
   - Returns: dict with all encrypted components

5. **`decrypt_oauth_tokens(access_token_encrypted, access_token_iv, access_token_auth_tag, refresh_token_encrypted, refresh_token_iv, refresh_token_auth_tag)`**
   - Decrypt both tokens
   - Returns: dict {access_token, refresh_token}

**Security Features**:
- AES-256-GCM (authenticated encryption)
- Random IV per encryption (never reuse)
- Authentication tag prevents tampering
- Base64-encoded key from environment

---

## API Layer (backend/app/api/)

### Auth Endpoints (`auth.py`)

**Router**: `/api/auth`

**Endpoints**:
1. `POST /register` → `register()`
2. `POST /login` → `login()`
3. `POST /refresh` → `refresh_token()`
4. `GET /me` → `get_current_user()` (protected)
5. `POST /change-password` → `change_password()` (protected)
6. `POST /logout` → `logout()` (protected)

**Dependency**: `get_current_tenant()` for protected routes

---

### eBay Accounts Endpoints (`ebay_accounts.py`)

**Router**: `/api/ebay-accounts`

**Endpoints**:
1. `GET /auth-url` → `get_authorization_url()` (protected)
2. `POST /callback` → `oauth_callback()` (protected)
3. `GET /` → `list_ebay_accounts()` (protected)
4. `GET /status` → `get_oauth_status()` (protected)
5. `DELETE /{account_id}` → `delete_ebay_account()` (protected)
6. `DELETE /oauth/disconnect` → `disconnect_oauth()` (protected)

**All endpoints require authentication via JWT**

---

## Configuration (`config.py`)

**Settings Class**: Pydantic BaseSettings

**Key Settings**:
- `APP_NAME`, `APP_VERSION`
- `DATABASE_URL`
- `SECRET_KEY` (JWT signing)
- `ENCRYPTION_KEY` (token encryption)
- `ACCESS_TOKEN_EXPIRE_MINUTES` (default: 1440 = 24h)
- `REFRESH_TOKEN_EXPIRE_DAYS` (default: 30)
- `EBAY_CLIENT_ID`, `EBAY_CLIENT_SECRET`
- `EBAY_REDIRECT_URI`, `EBAY_ENVIRONMENT`
- `CORS_ORIGINS`

**Environment**: Loaded from `.env` file
