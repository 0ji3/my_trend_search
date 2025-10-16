/**
 * Dashboard Page
 */
import React, { useEffect, useState } from 'react';
import {
  Box,
  Container,
  Typography,
  Paper,
  Button,
  Grid,
  Card,
  CardContent,
  CircularProgress,
  Alert,
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { useAppDispatch, useAppSelector } from '../store/hooks';
import { logout } from '../store/authSlice';
import EbayConnection from '../components/ebay/EbayConnection';
import AccountSwitcher from '../components/dashboard/AccountSwitcher';
import TrendingItemsList from '../components/dashboard/TrendingItemsList';
import PerformanceChart from '../components/dashboard/PerformanceChart';
import dashboardService, { DashboardSummary, DashboardPerformance } from '../services/dashboard.service';
import trendsService, { TrendAnalysis } from '../services/trends.service';
import ebayService from '../services/ebay.service';
import { EbayAccount } from '../types';
import ShowChartIcon from '@mui/icons-material/ShowChart';
import VisibilityIcon from '@mui/icons-material/Visibility';
import RemoveRedEyeIcon from '@mui/icons-material/RemoveRedEye';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';

const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const { user } = useAppSelector((state) => state.auth);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [performance, setPerformance] = useState<DashboardPerformance | null>(null);
  const [topTrending, setTopTrending] = useState<TrendAnalysis[]>([]);
  const [accounts, setAccounts] = useState<EbayAccount[]>([]);
  const [selectedAccountId, setSelectedAccountId] = useState<string | null>(null);

  useEffect(() => {
    loadAccounts();
  }, []);

  useEffect(() => {
    loadDashboardData();
  }, [selectedAccountId]);

  const loadAccounts = async () => {
    try {
      const accountsData = await ebayService.getAccounts();
      setAccounts(accountsData);
    } catch (err: any) {
      console.error('Failed to load accounts:', err);
    }
  };

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      setError(null);

      // 並列でデータを取得（アカウントIDパラメータ付き）
      const [summaryData, performanceData, trendsData] = await Promise.all([
        dashboardService.getSummary(selectedAccountId),
        dashboardService.getPerformance(7, selectedAccountId),
        trendsService.getTopTrending(10, selectedAccountId)
      ]);

      setSummary(summaryData);
      setPerformance(performanceData);
      setTopTrending(trendsData.trends);
    } catch (err: any) {
      console.error('Failed to load dashboard data:', err);
      setError(err.response?.data?.detail || 'Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  const handleAccountChange = (accountId: string | null) => {
    setSelectedAccountId(accountId);
  };

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

        {error && (
          <Alert severity="error" sx={{ mb: 3 }}>
            {error}
          </Alert>
        )}

        {/* Account Switcher */}
        {accounts.length > 0 && (
          <AccountSwitcher
            accounts={accounts}
            selectedAccountId={selectedAccountId}
            onAccountChange={handleAccountChange}
          />
        )}

        {/* KPI Cards */}
        <Grid container spacing={3}>
          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <ShowChartIcon color="primary" sx={{ mr: 1 }} />
                  <Typography variant="h6">
                    eBay Accounts
                  </Typography>
                </Box>
                {loading ? (
                  <CircularProgress size={40} />
                ) : (
                  <>
                    <Typography variant="h3" color="primary">
                      {summary?.total_accounts || 0}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Connected accounts
                    </Typography>
                  </>
                )}
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <VisibilityIcon color="primary" sx={{ mr: 1 }} />
                  <Typography variant="h6">
                    Active Listings
                  </Typography>
                </Box>
                {loading ? (
                  <CircularProgress size={40} />
                ) : (
                  <>
                    <Typography variant="h3" color="primary">
                      {summary?.active_listings || 0}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Total listings monitored
                    </Typography>
                  </>
                )}
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <RemoveRedEyeIcon color="info" sx={{ mr: 1 }} />
                  <Typography variant="h6">
                    Views Today
                  </Typography>
                </Box>
                {loading ? (
                  <CircularProgress size={40} />
                ) : (
                  <>
                    <Typography variant="h3" color="info.main">
                      {summary?.total_views_today?.toLocaleString() || 0}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Total views
                    </Typography>
                  </>
                )}
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <TrendingUpIcon color="success" sx={{ mr: 1 }} />
                  <Typography variant="h6">
                    Trending Items
                  </Typography>
                </Box>
                {loading ? (
                  <CircularProgress size={40} />
                ) : (
                  <>
                    <Typography variant="h3" color="success.main">
                      {summary?.trending_items_count || 0}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Items showing growth
                    </Typography>
                  </>
                )}
              </CardContent>
            </Card>
          </Grid>

          {/* eBay Connection */}
          <Grid item xs={12}>
            <EbayConnection />
          </Grid>

          {/* Performance Chart */}
          <Grid item xs={12}>
            <PerformanceChart performance={performance} loading={loading} />
          </Grid>

          {/* Trending Items List */}
          <Grid item xs={12}>
            <TrendingItemsList trends={topTrending} loading={loading} />
          </Grid>

          {/* Getting Started Guide (only show if no data) */}
          {!loading && summary?.active_listings === 0 && (
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
                      Connect your eBay account above to start monitoring your listings
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
              </Paper>
            </Grid>
          )}
        </Grid>

        {/* Account Information */}
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
