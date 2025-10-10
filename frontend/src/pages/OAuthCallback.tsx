/**
 * OAuth Callback Page
 * Handles eBay OAuth redirect
 */
import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Box, Container, Paper, Typography, CircularProgress, Alert } from '@mui/material';
import ebayService from '../services/ebay.service';

const OAuthCallback: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [status, setStatus] = useState<'processing' | 'success' | 'error'>('processing');
  const [message, setMessage] = useState('Processing eBay authorization...');

  useEffect(() => {
    handleCallback();
  }, []);

  const handleCallback = async () => {
    try {
      // Get authorization code from URL
      const code = searchParams.get('code');
      const state = searchParams.get('state');
      const error = searchParams.get('error');

      // Check for error from eBay
      if (error) {
        setStatus('error');
        setMessage(`eBay authorization failed: ${error}`);
        setTimeout(() => navigate('/dashboard'), 3000);
        return;
      }

      // Check if code exists
      if (!code) {
        setStatus('error');
        setMessage('No authorization code received from eBay');
        setTimeout(() => navigate('/dashboard'), 3000);
        return;
      }

      // Validate state (optional, for CSRF protection)
      const storedState = sessionStorage.getItem('ebay_oauth_state');
      if (state && storedState && state !== storedState) {
        setStatus('error');
        setMessage('Invalid state parameter. Possible CSRF attack.');
        setTimeout(() => navigate('/dashboard'), 3000);
        return;
      }

      // Exchange code for tokens
      setMessage('Connecting to eBay...');
      await ebayService.handleCallback(code, state || undefined);

      // Success
      setStatus('success');
      setMessage('eBay account connected successfully! Redirecting...');

      // Clear stored state
      sessionStorage.removeItem('ebay_oauth_state');

      // Redirect to dashboard
      setTimeout(() => navigate('/dashboard'), 2000);
    } catch (err: any) {
      console.error('OAuth callback error:', err);
      setStatus('error');
      setMessage(err.response?.data?.detail || 'Failed to connect eBay account');
      setTimeout(() => navigate('/dashboard'), 3000);
    }
  };

  return (
    <Box
      sx={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: '100vh',
        bgcolor: 'background.default',
      }}
    >
      <Container maxWidth="sm">
        <Paper
          elevation={3}
          sx={{
            p: 4,
            textAlign: 'center',
          }}
        >
          {status === 'processing' && (
            <>
              <CircularProgress size={60} sx={{ mb: 3 }} />
              <Typography variant="h5" gutterBottom>
                Connecting eBay Account
              </Typography>
              <Typography variant="body1" color="text.secondary">
                {message}
              </Typography>
            </>
          )}

          {status === 'success' && (
            <>
              <Alert severity="success" sx={{ mb: 3 }}>
                Success!
              </Alert>
              <Typography variant="h5" gutterBottom>
                eBay Account Connected
              </Typography>
              <Typography variant="body1" color="text.secondary">
                {message}
              </Typography>
            </>
          )}

          {status === 'error' && (
            <>
              <Alert severity="error" sx={{ mb: 3 }}>
                Connection Failed
              </Alert>
              <Typography variant="h5" gutterBottom>
                Failed to Connect
              </Typography>
              <Typography variant="body1" color="text.secondary">
                {message}
              </Typography>
            </>
          )}
        </Paper>
      </Container>
    </Box>
  );
};

export default OAuthCallback;
