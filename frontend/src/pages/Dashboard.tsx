/**
 * Dashboard Page
 */
import React from 'react';
import {
  Box,
  Container,
  Typography,
  Paper,
  Button,
  Grid,
  Card,
  CardContent,
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { useAppDispatch, useAppSelector } from '../store/hooks';
import { logout } from '../store/authSlice';

const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const { user } = useAppSelector((state) => state.auth);

  const handleLogout = async () => {
    await dispatch(logout());
    navigate('/login');
  };

  return (
    <Box sx={{ bgcolor: 'background.default', minHeight: '100vh', py: 4 }}>
      <Container maxWidth="lg">
        <Paper elevation={2} sx={{ p: 3, mb: 3 }}>
          <Box
            sx={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}
          >
            <Box>
              <Typography variant="h4" gutterBottom>
                Dashboard
              </Typography>
              <Typography variant="body1" color="text.secondary">
                Welcome back, {user?.email}!
              </Typography>
              {user?.business_name && (
                <Typography variant="body2" color="text.secondary">
                  {user.business_name}
                </Typography>
              )}
            </Box>
            <Button variant="outlined" onClick={handleLogout}>
              Logout
            </Button>
          </Box>
        </Paper>

        <Grid container spacing={3}>
          <Grid item xs={12} md={4}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  eBay Accounts
                </Typography>
                <Typography variant="h3" color="primary">
                  0
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Connected accounts
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={4}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Active Listings
                </Typography>
                <Typography variant="h3" color="primary">
                  0
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Total listings monitored
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={4}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Trending Items
                </Typography>
                <Typography variant="h3" color="success.main">
                  0
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Items showing growth
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                Getting Started
              </Typography>
              <Typography variant="body1" paragraph>
                Welcome to eBay Trend Research Tool! Here's how to get started:
              </Typography>
              <ol>
                <li>
                  <Typography variant="body2" paragraph>
                    Connect your eBay account to start monitoring your listings
                  </Typography>
                </li>
                <li>
                  <Typography variant="body2" paragraph>
                    The system will automatically sync your active listings daily
                  </Typography>
                </li>
                <li>
                  <Typography variant="body2" paragraph>
                    View trending items with high View and Watch growth rates
                  </Typography>
                </li>
                <li>
                  <Typography variant="body2">
                    Analyze performance metrics to optimize your listing strategy
                  </Typography>
                </li>
              </ol>
              <Button variant="contained" sx={{ mt: 2 }} disabled>
                Connect eBay Account (Coming Soon)
              </Button>
            </Paper>
          </Grid>
        </Grid>

        <Paper sx={{ p: 3, mt: 3 }}>
          <Typography variant="h6" gutterBottom>
            Account Information
          </Typography>
          <Grid container spacing={2}>
            <Grid item xs={12} sm={6}>
              <Typography variant="body2" color="text.secondary">
                Email:
              </Typography>
              <Typography variant="body1">{user?.email}</Typography>
            </Grid>
            <Grid item xs={12} sm={6}>
              <Typography variant="body2" color="text.secondary">
                Business Name:
              </Typography>
              <Typography variant="body1">
                {user?.business_name || 'Not set'}
              </Typography>
            </Grid>
            <Grid item xs={12} sm={6}>
              <Typography variant="body2" color="text.secondary">
                Timezone:
              </Typography>
              <Typography variant="body1">{user?.timezone}</Typography>
            </Grid>
            <Grid item xs={12} sm={6}>
              <Typography variant="body2" color="text.secondary">
                Status:
              </Typography>
              <Typography variant="body1" sx={{ textTransform: 'capitalize' }}>
                {user?.status}
              </Typography>
            </Grid>
          </Grid>
        </Paper>
      </Container>
    </Box>
  );
};

export default Dashboard;
