/**
 * eBay Connection Component
 */
import React, { useState, useEffect } from 'react';
import {
  Box,
  Button,
  Card,
  CardContent,
  Typography,
  Alert,
  CircularProgress,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  Chip,
} from '@mui/material';
import { Delete as DeleteIcon, CheckCircle as CheckCircleIcon } from '@mui/icons-material';
import ebayService from '../../services/ebay.service';
import { OAuthStatus } from '../../types';

const EbayConnection: React.FC = () => {
  const [status, setStatus] = useState<OAuthStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [connecting, setConnecting] = useState(false);

  useEffect(() => {
    loadStatus();
  }, []);

  const loadStatus = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await ebayService.getOAuthStatus();
      setStatus(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load eBay connection status');
      console.error('Failed to load status:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleConnect = async () => {
    try {
      setConnecting(true);
      setError(null);
      await ebayService.connectEbayAccount();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to initiate eBay connection');
      console.error('Failed to connect:', err);
      setConnecting(false);
    }
  };

  const handleDisconnect = async () => {
    if (!window.confirm('Are you sure you want to disconnect your eBay account? This will remove all connected accounts and stop data synchronization.')) {
      return;
    }

    try {
      setError(null);
      await ebayService.disconnectOAuth();
      await loadStatus();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to disconnect eBay account');
      console.error('Failed to disconnect:', err);
    }
  };

  const handleDeleteAccount = async (accountId: string) => {
    if (!window.confirm('Are you sure you want to delete this eBay account?')) {
      return;
    }

    try {
      setError(null);
      await ebayService.deleteAccount(accountId);
      await loadStatus();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete account');
      console.error('Failed to delete account:', err);
    }
  };

  if (loading) {
    return (
      <Card>
        <CardContent>
          <Box display="flex" justifyContent="center" alignItems="center" minHeight={200}>
            <CircularProgress />
          </Box>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
          <Typography variant="h6">eBay Account Connection</Typography>
          {status?.is_connected && (
            <Chip
              icon={<CheckCircleIcon />}
              label="Connected"
              color="success"
              size="small"
            />
          )}
        </Box>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {!status?.is_connected ? (
          <Box>
            <Typography variant="body2" color="text.secondary" paragraph>
              Connect your eBay seller account to start monitoring your listings and discovering trending items.
            </Typography>
            <Button
              variant="contained"
              color="primary"
              onClick={handleConnect}
              disabled={connecting}
            >
              {connecting ? 'Connecting...' : 'Connect eBay Account'}
            </Button>
          </Box>
        ) : (
          <Box>
            <Box mb={2}>
              <Typography variant="body2" color="text.secondary">
                Token Status:{' '}
                {status.has_valid_token ? (
                  <Chip label="Valid" color="success" size="small" />
                ) : (
                  <Chip label="Expired" color="warning" size="small" />
                )}
              </Typography>
              {status.access_token_expires_at && (
                <Typography variant="body2" color="text.secondary" mt={0.5}>
                  Expires: {new Date(status.access_token_expires_at).toLocaleString()}
                </Typography>
              )}
            </Box>

            {status.accounts && status.accounts.length > 0 && (
              <Box mb={2}>
                <Typography variant="subtitle2" gutterBottom>
                  Connected Accounts ({status.accounts_count})
                </Typography>
                <List dense>
                  {status.accounts.map((account) => (
                    <ListItem key={account.id}>
                      <ListItemText
                        primary={account.username || account.ebay_user_id}
                        secondary={
                          <>
                            {account.email && <span>{account.email} • </span>}
                            {account.marketplace_id}
                            {account.last_sync_at && (
                              <> • Last sync: {new Date(account.last_sync_at).toLocaleString()}</>
                            )}
                          </>
                        }
                      />
                      <ListItemSecondaryAction>
                        <IconButton
                          edge="end"
                          aria-label="delete"
                          onClick={() => handleDeleteAccount(account.id)}
                        >
                          <DeleteIcon />
                        </IconButton>
                      </ListItemSecondaryAction>
                    </ListItem>
                  ))}
                </List>
              </Box>
            )}

            <Box>
              <Button
                variant="outlined"
                color="error"
                onClick={handleDisconnect}
                sx={{ mr: 1 }}
              >
                Disconnect OAuth
              </Button>
              <Button
                variant="outlined"
                onClick={loadStatus}
              >
                Refresh Status
              </Button>
            </Box>
          </Box>
        )}
      </CardContent>
    </Card>
  );
};

export default EbayConnection;
