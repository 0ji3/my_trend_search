/**
 * TrendingItemsList Component
 *
 * トレンドTOP10商品の一覧表示
 */
import React from 'react';
import {
  List,
  ListItem,
  ListItemAvatar,
  Avatar,
  ListItemText,
  Chip,
  Typography,
  Box,
  Paper,
  Skeleton
} from '@mui/material';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import { TrendAnalysis } from '../../services/trends.service';

interface TrendingItemsListProps {
  trends: TrendAnalysis[];
  loading?: boolean;
}

const TrendingItemsList: React.FC<TrendingItemsListProps> = ({ trends, loading = false }) => {
  if (loading) {
    return (
      <Paper sx={{ p: 2 }}>
        <Typography variant="h6" gutterBottom>
          トレンド TOP 10
        </Typography>
        <List>
          {[...Array(5)].map((_, index) => (
            <ListItem key={index}>
              <ListItemAvatar>
                <Skeleton variant="circular" width={56} height={56} />
              </ListItemAvatar>
              <ListItemText
                primary={<Skeleton width="80%" />}
                secondary={<Skeleton width="40%" />}
              />
            </ListItem>
          ))}
        </List>
      </Paper>
    );
  }

  if (!trends || trends.length === 0) {
    return (
      <Paper sx={{ p: 3, textAlign: 'center' }}>
        <Typography variant="h6" gutterBottom>
          トレンド TOP 10
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
          トレンドデータがありません
        </Typography>
      </Paper>
    );
  }

  return (
    <Paper sx={{ p: 2 }}>
      <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <TrendingUpIcon color="primary" />
        トレンド TOP 10
      </Typography>
      <List>
        {trends.map((trend, index) => (
          <ListItem
            key={trend.id}
            sx={{
              borderRadius: 1,
              mb: 1,
              '&:hover': {
                bgcolor: 'action.hover',
                cursor: 'pointer'
              }
            }}
          >
            <Box
              sx={{
                minWidth: 32,
                height: 32,
                borderRadius: '50%',
                bgcolor: index < 3 ? 'primary.main' : 'grey.400',
                color: 'white',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontWeight: 'bold',
                mr: 2
              }}
            >
              {trend.rank || index + 1}
            </Box>
            <ListItemAvatar>
              <Avatar
                src={trend.image_url || undefined}
                variant="rounded"
                sx={{ width: 56, height: 56 }}
              >
                {!trend.image_url && trend.title?.charAt(0).toUpperCase()}
              </Avatar>
            </ListItemAvatar>
            <ListItemText
              primary={
                <Typography variant="body1" noWrap sx={{ fontWeight: 500 }}>
                  {trend.title}
                </Typography>
              }
              secondary={
                <Box sx={{ mt: 0.5 }}>
                  <Typography variant="body2" color="text.secondary" component="span">
                    {trend.currency} {trend.price ? Number(trend.price).toFixed(2) : 'N/A'}
                  </Typography>
                  {trend.category_name && (
                    <Typography
                      variant="caption"
                      color="text.secondary"
                      component="span"
                      sx={{ ml: 1 }}
                    >
                      • {trend.category_name}
                    </Typography>
                  )}
                </Box>
              }
            />
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5, minWidth: 120 }}>
              <Chip
                label={`スコア: ${Number(trend.trend_score).toFixed(1)}`}
                size="small"
                color="success"
                sx={{ fontWeight: 600 }}
              />
              {trend.view_growth_rate !== null && trend.view_growth_rate !== undefined && (
                <Typography variant="caption" color="text.secondary">
                  View: +{Number(trend.view_growth_rate).toFixed(1)}%
                </Typography>
              )}
              {trend.watch_growth_rate !== null && trend.watch_growth_rate !== undefined && (
                <Typography variant="caption" color="text.secondary">
                  Watch: +{Number(trend.watch_growth_rate).toFixed(1)}%
                </Typography>
              )}
            </Box>
          </ListItem>
        ))}
      </List>
    </Paper>
  );
};

export default TrendingItemsList;
