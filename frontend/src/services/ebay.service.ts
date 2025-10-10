/**
 * eBay OAuth Service
 */
import apiClient from './api';
import { OAuthAuthorizationURL, OAuthStatus, EbayAccount } from '../types';

class EbayService {
  /**
   * Get eBay OAuth authorization URL
   */
  async getAuthorizationURL(): Promise<OAuthAuthorizationURL> {
    const response = await apiClient.get<OAuthAuthorizationURL>('/ebay-accounts/auth-url');
    return response.data;
  }

  /**
   * Handle OAuth callback (exchange code for tokens)
   */
  async handleCallback(code: string, state?: string): Promise<void> {
    await apiClient.post('/ebay-accounts/callback', {
      code,
      state,
    });
  }

  /**
   * Get OAuth connection status
   */
  async getOAuthStatus(): Promise<OAuthStatus> {
    const response = await apiClient.get<OAuthStatus>('/ebay-accounts/status');
    return response.data;
  }

  /**
   * Get list of connected eBay accounts
   */
  async getAccounts(): Promise<EbayAccount[]> {
    const response = await apiClient.get<{ accounts: EbayAccount[]; total: number }>('/ebay-accounts/');
    return response.data.accounts;
  }

  /**
   * Delete an eBay account
   */
  async deleteAccount(accountId: string): Promise<void> {
    await apiClient.delete(`/ebay-accounts/${accountId}`);
  }

  /**
   * Disconnect OAuth (delete all credentials and accounts)
   */
  async disconnectOAuth(): Promise<void> {
    await apiClient.delete('/ebay-accounts/oauth/disconnect');
  }

  /**
   * Initiate eBay OAuth flow
   * Opens eBay authorization page in a new window
   */
  async connectEbayAccount(): Promise<void> {
    try {
      const { authorization_url, state } = await this.getAuthorizationURL();

      // Store state in session storage for validation
      sessionStorage.setItem('ebay_oauth_state', state);

      // Open eBay authorization page
      window.location.href = authorization_url;
    } catch (error) {
      console.error('Failed to initiate eBay OAuth:', error);
      throw error;
    }
  }
}

export default new EbayService();
