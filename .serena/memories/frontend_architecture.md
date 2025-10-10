# Frontend Architecture Overview

## Technology Stack

- **Framework**: React 18.2 with TypeScript
- **UI Library**: Material-UI (MUI) v5
- **State Management**: Redux Toolkit with typed hooks
- **Routing**: React Router DOM v6
- **HTTP Client**: Axios with interceptors
- **Build Tool**: Vite (assumed from modern React setup)

## Directory Structure

```
frontend/src/
├── components/          # Reusable UI components
│   ├── common/         # Shared components
│   │   └── PrivateRoute.tsx    # Auth route protection
│   └── ebay/           # eBay-specific components
│       └── EbayConnection.tsx  # OAuth connection management
│
├── pages/              # Route-level page components
│   ├── Login.tsx       # Login page with form
│   ├── Register.tsx    # Registration page
│   ├── Dashboard.tsx   # Main dashboard (KPIs + eBay connection)
│   └── OAuthCallback.tsx  # eBay OAuth callback handler
│
├── services/           # API communication layer
│   ├── api.ts          # Axios instance with auth interceptor
│   ├── auth.service.ts # Authentication API calls
│   └── ebay.service.ts # eBay OAuth API calls
│
├── store/              # Redux state management
│   ├── store.ts        # Redux store configuration
│   ├── hooks.ts        # Typed useDispatch/useSelector
│   └── authSlice.ts    # Auth state slice (user, tokens, loading)
│
├── theme/              # MUI theming
│   └── theme.ts        # Custom theme configuration
│
├── types/              # TypeScript type definitions
│   └── index.ts        # Shared types (User, Auth, eBay, etc.)
│
├── App.tsx             # Root component with routing
└── index.tsx           # Entry point
```

## Key Components

### Authentication Components

#### PrivateRoute (`components/common/PrivateRoute.tsx`)
- **Purpose**: Protect routes requiring authentication
- **Logic**: Checks Redux auth state, redirects to /login if not authenticated
- **Usage**: Wraps Dashboard and OAuthCallback routes

#### Login Page (`pages/Login.tsx`)
- **Features**: Email/password form, validation, error handling
- **Actions**: Dispatches `login` thunk, navigates to /dashboard on success
- **UI**: Material-UI Card with TextField, Button, CircularProgress

#### Register Page (`pages/Register.tsx`)
- **Features**: Email/password/business_name form, validation
- **Actions**: Dispatches `register` thunk, navigates to /dashboard
- **UI**: Similar to Login with additional fields

### eBay OAuth Components

#### EbayConnection (`components/ebay/EbayConnection.tsx`)
- **Purpose**: Display eBay connection status and manage OAuth
- **State**: OAuthStatus, loading, error, connecting
- **Methods**:
  - `loadStatus()`: Fetch current OAuth status
  - `handleConnect()`: Initiate OAuth flow (redirects to eBay)
  - `handleDisconnect()`: Revoke OAuth credentials
  - `handleDeleteAccount()`: Remove specific eBay account
- **UI Elements**:
  - Connection status chip (Connected/Disconnected)
  - Token validity indicator (Valid/Expired)
  - Token expiration timestamp
  - Connected accounts list with delete buttons
  - Connect/Disconnect/Refresh buttons

#### OAuthCallback (`pages/OAuthCallback.tsx`)
- **Purpose**: Handle eBay OAuth redirect after user authorization
- **Flow**:
  1. Extract `code`, `state`, `error` from URL query params
  2. Validate state parameter (CSRF protection)
  3. Call backend `/callback` endpoint with code
  4. Show processing/success/error states
  5. Auto-redirect to dashboard after 2-3 seconds
- **States**: processing, success, error
- **UI**: CircularProgress, Alert, Typography with status messages

#### Dashboard (`pages/Dashboard.tsx`)
- **Features**:
  - User welcome message with email/business_name
  - Logout button
  - KPI cards (eBay Accounts, Active Listings, Trending Items) - currently hardcoded 0
  - EbayConnection component integration
  - Getting Started instructions
  - Account information grid
- **Redux**: Uses `useAppSelector` to access auth.user

## Services Layer

### API Client (`services/api.ts`)
```typescript
const apiClient = axios.create({
  baseURL: 'http://localhost:8000/api',
  headers: { 'Content-Type': 'application/json' }
});

// Request interceptor: Inject access token
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Response interceptor: Auto-refresh on 401
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      const refreshToken = localStorage.getItem('refresh_token');
      const { access_token } = await authService.refreshToken(refreshToken);
      localStorage.setItem('access_token', access_token);
      originalRequest.headers.Authorization = `Bearer ${access_token}`;
      return apiClient(originalRequest);
    }
    return Promise.reject(error);
  }
);
```

### Auth Service (`services/auth.service.ts`)
- `login(email, password)`: POST /auth/login
- `register(userData)`: POST /auth/register
- `refreshToken(refreshToken)`: POST /auth/refresh
- `logout()`: POST /auth/logout
- `getCurrentUser()`: GET /auth/me

### eBay Service (`services/ebay.service.ts`)
- `getAuthorizationURL()`: GET /ebay-accounts/auth-url
- `handleCallback(code, state)`: POST /ebay-accounts/callback
- `getOAuthStatus()`: GET /ebay-accounts/status
- `getAccounts()`: GET /ebay-accounts/
- `deleteAccount(accountId)`: DELETE /ebay-accounts/{id}
- `disconnectOAuth()`: DELETE /ebay-accounts/oauth/disconnect
- `connectEbayAccount()`: Stores state in sessionStorage, redirects to eBay auth URL

## Redux Store

### Store Configuration (`store/store.ts`)
```typescript
export const store = configureStore({
  reducer: {
    auth: authReducer,
    // Future: trends, listings, dashboard
  },
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
```

### Auth Slice (`store/authSlice.ts`)
**State**:
```typescript
{
  user: User | null,
  access_token: string | null,
  refresh_token: string | null,
  isAuthenticated: boolean,
  loading: boolean,
  error: string | null
}
```

**Thunks**:
- `login`: Async thunk calling authService.login, stores tokens in localStorage
- `register`: Async thunk calling authService.register
- `logout`: Clears tokens from localStorage and state
- `checkAuth`: Validates current token by fetching user info

**Reducers**:
- `login.fulfilled`: Sets user, tokens, isAuthenticated=true
- `register.fulfilled`: Same as login.fulfilled
- `logout.fulfilled`: Resets state to initial
- `checkAuth.fulfilled`: Updates user data

### Typed Hooks (`store/hooks.ts`)
```typescript
export const useAppDispatch = () => useDispatch<AppDispatch>();
export const useAppSelector: TypedUseSelectorHook<RootState> = useSelector;
```

## Type Definitions (`types/index.ts`)

### Core Types
```typescript
interface User {
  id: string;
  email: string;
  business_name?: string;
  timezone: string;
  status: string;
  created_at: string;
}

interface LoginCredentials {
  email: string;
  password: string;
}

interface RegisterData {
  email: string;
  password: string;
  business_name?: string;
  timezone?: string;
}

interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}
```

### eBay Types
```typescript
interface OAuthAuthorizationURL {
  authorization_url: string;
  state: string;
}

interface EbayAccount {
  id: string;
  tenant_id: string;
  oauth_credential_id: string;
  ebay_user_id: string;
  username?: string;
  email?: string;
  marketplace_id: string;
  is_active: boolean;
  last_sync_at?: string;
  created_at: string;
  updated_at: string;
}

interface OAuthStatus {
  is_connected: boolean;
  has_valid_token: boolean;
  access_token_expires_at?: string;
  accounts_count: number;
  accounts: EbayAccount[];
}
```

## Routing Structure (`App.tsx`)

```typescript
<Router>
  <Routes>
    {/* Public Routes */}
    <Route path="/login" element={<Login />} />
    <Route path="/register" element={<Register />} />

    {/* Protected Routes */}
    <Route path="/oauth/callback" element={
      <PrivateRoute><OAuthCallback /></PrivateRoute>
    } />
    <Route path="/dashboard" element={
      <PrivateRoute><Dashboard /></PrivateRoute>
    } />

    {/* Default & Catch-all */}
    <Route path="/" element={<Navigate to="/dashboard" replace />} />
    <Route path="*" element={<Navigate to="/dashboard" replace />} />
  </Routes>
</Router>
```

## Theme Configuration (`theme/theme.ts`)

```typescript
export const theme = createTheme({
  palette: {
    primary: { main: '#1976d2' },
    secondary: { main: '#dc004e' },
    background: { default: '#f5f5f5' }
  },
  typography: {
    fontFamily: 'Roboto, Arial, sans-serif',
  },
});
```

## Implementation Status

### ✅ Completed (Phase 2 & 3)
- Authentication flow (login, register, logout, token refresh)
- Protected routing
- eBay OAuth authorization URL generation
- OAuth callback handling with CSRF protection
- OAuth status display
- Account connection/disconnection UI
- Redux state management for auth
- API client with auto-refresh interceptor

### 🔜 Future Frontend Work
- Listings page (Phase 4)
- Trend analysis visualization (Phase 5)
- Dashboard KPI integration (Phase 6)
- Real-time notifications (Phase 7)
- Charts with Recharts library
- Advanced filtering and search
