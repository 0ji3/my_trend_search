/**
 * Type Definitions
 */

// User/Tenant types
export interface User {
  id: string;
  email: string;
  business_name?: string;
  timezone: string;
  status: string;
  created_at: string;
  updated_at: string;
}

// Authentication types
export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  business_name?: string;
  timezone?: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface PasswordChangeRequest {
  current_password: string;
  new_password: string;
}

// API Error types
export interface APIError {
  detail: string;
  status?: number;
}

// Auth State
export interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}

// eBay OAuth types
export interface OAuthAuthorizationURL {
  authorization_url: string;
  state: string;
}

export interface EbayAccount {
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

export interface OAuthStatus {
  is_connected: boolean;
  has_valid_token: boolean;
  access_token_expires_at?: string;
  accounts_count: number;
  accounts: EbayAccount[];
}
