/**
 * PerformanceChart Component
 *
 * パフォーマンス推移グラフ（Recharts使用）
 */
import React from 'react';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts';
import { Paper, Typography, Box, Skeleton, Tabs, Tab } from '@mui/material';
import { DashboardPerformance } from '../../services/dashboard.service';

interface PerformanceChartProps {
  performance: DashboardPerformance | null;
  loading?: boolean;
}

const PerformanceChart: React.FC<PerformanceChartProps> = ({ performance, loading = false }) => {
  const [tabValue, setTabValue] = React.useState(0);

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  if (loading) {
    return (
      <Paper sx={{ p: 2 }}>
        <Typography variant="h6" gutterBottom>
          パフォーマンス推移
        </Typography>
        <Skeleton variant="rectangular" height={300} />
      </Paper>
    );
  }

  if (!performance || performance.dates.length === 0) {
    return (
      <Paper sx={{ p: 3, textAlign: 'center' }}>
        <Typography variant="h6" gutterBottom>
          パフォーマンス推移
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
          パフォーマンスデータがありません
        </Typography>
      </Paper>
    );
  }

  // データを変換（日付を短縮形式に）
  const chartData = performance.dates.map((date, index) => {
    const dateObj = new Date(date);
    const shortDate = `${dateObj.getMonth() + 1}/${dateObj.getDate()}`;

    return {
      date: shortDate,
      fullDate: date,
      views: performance.total_views[index],
      watches: performance.total_watches[index],
      trendScore: performance.avg_trend_score[index],
      trendingCount: performance.trending_count[index]
    };
  });

  return (
    <Paper sx={{ p: 2 }}>
      <Box sx={{ mb: 2 }}>
        <Typography variant="h6" gutterBottom>
          パフォーマンス推移
        </Typography>
        <Tabs value={tabValue} onChange={handleTabChange}>
          <Tab label="View & Watch数" />
          <Tab label="トレンドスコア" />
        </Tabs>
      </Box>

      {tabValue === 0 && (
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 12 }}
              angle={-45}
              textAnchor="end"
              height={60}
            />
            <YAxis yAxisId="left" tick={{ fontSize: 12 }} />
            <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 12 }} />
            <Tooltip
              contentStyle={{ backgroundColor: '#fff', border: '1px solid #ccc' }}
              labelStyle={{ fontWeight: 'bold' }}
            />
            <Legend />
            <Line
              yAxisId="left"
              type="monotone"
              dataKey="views"
              stroke="#8884d8"
              strokeWidth={2}
              name="View数"
              dot={{ r: 4 }}
              activeDot={{ r: 6 }}
            />
            <Line
              yAxisId="right"
              type="monotone"
              dataKey="watches"
              stroke="#82ca9d"
              strokeWidth={2}
              name="Watch数"
              dot={{ r: 4 }}
              activeDot={{ r: 6 }}
            />
          </LineChart>
        </ResponsiveContainer>
      )}

      {tabValue === 1 && (
        <ResponsiveContainer width="100%" height={300}>
          <AreaChart data={chartData}>
            <defs>
              <linearGradient id="colorScore" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#ff7300" stopOpacity={0.8} />
                <stop offset="95%" stopColor="#ff7300" stopOpacity={0.1} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 12 }}
              angle={-45}
              textAnchor="end"
              height={60}
            />
            <YAxis yAxisId="left" tick={{ fontSize: 12 }} />
            <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 12 }} />
            <Tooltip
              contentStyle={{ backgroundColor: '#fff', border: '1px solid #ccc' }}
              labelStyle={{ fontWeight: 'bold' }}
            />
            <Legend />
            <Area
              yAxisId="left"
              type="monotone"
              dataKey="trendScore"
              stroke="#ff7300"
              strokeWidth={2}
              fillOpacity={1}
              fill="url(#colorScore)"
              name="平均トレンドスコア"
            />
            <Line
              yAxisId="right"
              type="monotone"
              dataKey="trendingCount"
              stroke="#413ea0"
              strokeWidth={2}
              name="トレンド商品数"
              dot={{ r: 4 }}
              activeDot={{ r: 6 }}
            />
          </AreaChart>
        </ResponsiveContainer>
      )}
    </Paper>
  );
};

export default PerformanceChart;
