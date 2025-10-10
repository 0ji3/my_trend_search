# Backend Models Overview

## SQLAlchemy Models (backend/app/models/)

### 1. Tenant Model (`tenant.py`)

**Purpose**: Main user/tenant model for multi-tenant SaaS

**Classes**:
- `TenantStatus(str, enum.Enum)`: Status enum (ACTIVE, INACTIVE, SUSPENDED)
- `Tenant(Base)`: User account model

**Tenant Fields**:
- `id`: UUID primary key
- `email`: Unique, indexed
- `password_hash`: bcrypt hashed password
- `business_name`: Optional company name
- `timezone`: Default UTC
- `status`: String (active/inactive/suspended)
- `created_at`, `updated_at`: Timestamps

**Relationships**:
- `oauth_credential`: One-to-one with OAuthCredential
- `ebay_accounts`: One-to-many with EbayAccount

**Methods**:
- `to_dict()`: Convert to dict (excludes password)

**Security Notes**:
- Passwords hashed with bcrypt (cost factor 12)
- Email validation via Pydantic
- Status stored as string to avoid enum issues

---

### 2. OAuthCredential Model (`oauth_credential.py`)

**Purpose**: Store encrypted eBay OAuth tokens (AES-256-GCM)

**Class**: `OAuthCredential(Base)`

**Fields**:
- `id`: UUID primary key
- `tenant_id`: Foreign key to tenants (unique, one-to-one)
- **Access Token (encrypted)**:
  - `access_token_encrypted`: LargeBinary
  - `access_token_iv`: LargeBinary (12 bytes IV)
  - `access_token_auth_tag`: LargeBinary (16 bytes)
- **Refresh Token (encrypted)**:
  - `refresh_token_encrypted`: LargeBinary
  - `refresh_token_iv`: LargeBinary
  - `refresh_token_auth_tag`: LargeBinary
- `access_token_expires_at`: DateTime
- `refresh_token_expires_at`: DateTime (nullable)
- `scopes`: ARRAY of strings
- `is_valid`: Boolean
- `created_at`, `updated_at`: Timestamps

**Relationships**:
- `tenant`: Many-to-one with Tenant
- `ebay_accounts`: One-to-many with EbayAccount

**Methods**:
- `to_dict()`: Convert to dict (excludes encrypted data)
- `is_access_token_expired()`: Check if access token expired
- `is_refresh_token_expired()`: Check if refresh token expired

**Security**:
- Tokens encrypted with AES-256-GCM before storage
- Separate IV and auth tag for each token
- Never expose encrypted data in API responses

---

### 3. EbayAccount Model (`ebay_account.py`)

**Purpose**: Store eBay seller account information

**Class**: `EbayAccount(Base)`

**Fields**:
- `id`: UUID primary key
- `oauth_credential_id`: Foreign key to oauth_credentials
- `tenant_id`: Foreign key to tenants
- `ebay_user_id`: Unique eBay user ID (indexed)
- `username`: eBay username
- `email`: Account email
- `marketplace_id`: EBAY_US, EBAY_UK, etc.
- `is_active`: Boolean
- `last_sync_at`: Last successful sync timestamp
- `created_at`, `updated_at`: Timestamps

**Relationships**:
- `tenant`: Many-to-one with Tenant
- `oauth_credential`: Many-to-one with OAuthCredential
- `listings`: One-to-many with Listing (future)

**Methods**:
- `to_dict()`: Convert to dict

**Notes**:
- One OAuth credential can have multiple eBay accounts (multi-user grant)
- Each account tracked separately for sync status

---

## Model Registration

**File**: `backend/app/models/__init__.py`

Exports:
- `Tenant`
- `TenantStatus`
- `OAuthCredential`
- `EbayAccount`

All models imported in `alembic/env.py` for migration auto-generation.

---

## Database Relationships Diagram

```
┌─────────────┐
│   Tenant    │
│  (User)     │
└──────┬──────┘
       │
       │ 1:1
       ▼
┌─────────────────┐
│ OAuthCredential │
│ (Encrypted)     │
└────────┬────────┘
         │
         │ 1:N
         ▼
┌─────────────────┐
│  EbayAccount    │
│ (Seller Info)   │
└─────────────────┘
         │
         │ 1:N (future)
         ▼
┌─────────────────┐
│    Listing      │
│  (Products)     │
└─────────────────┘
```

---

## Migration Status

**Current Migration**: `20251010_1043_196c5f590a3f_initial_schema_with_oauth.py`

**Created Tables**:
1. tenants
2. oauth_credentials
3. ebay_accounts
4. alembic_version

**Indexes**:
- tenants: `ix_tenants_email`
- oauth_credentials: `ix_oauth_credentials_tenant_id`
- ebay_accounts: `ix_ebay_accounts_ebay_user_id`, `ix_ebay_accounts_oauth_credential_id`, `ix_ebay_accounts_tenant_id`
