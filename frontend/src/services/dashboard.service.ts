/**
 * Dashboard API Service
 *
 * ダッシュボードのKPIとパフォーマンスデータを取得
 */
import api from './api';

export interface DashboardSummary {
  active_listings: number;
  total_views_today: number;
  total_watches_today: number;
  trending_items_count: number;
  top_trending_score: number;
  total_accounts: number;
}

export interface DashboardPerformance {
  dates: string[];
  total_views: number[];
  total_watches: number[];
  avg_trend_score: number[];
  trending_count: number[];
}

export interface RecentActivity {
  listing_id: string;
  item_id: string;
  title: string;
  price: number | null;
  currency: string;
  updated_at: string | null;
}

const dashboardService = {
  /**
   * ダッシュボードサマリーを取得
   */
  getSummary: async (): Promise<DashboardSummary> => {
    const response = await api.get<DashboardSummary>('/dashboard/summary');
    return response.data;
  },

  /**
   * パフォーマンス推移を取得
   * @param days 取得日数（デフォルト7日間）
   */
  getPerformance: async (days: number = 7): Promise<DashboardPerformance> => {
    const response = await api.get<DashboardPerformance>('/dashboard/performance', {
      params: { days }
    });
    return response.data;
  },

  /**
   * 最近のアクティビティを取得
   * @param limit 取得件数（デフォルト10件）
   */
  getRecentActivities: async (limit: number = 10): Promise<RecentActivity[]> => {
    const response = await api.get<{ activities: RecentActivity[] }>('/dashboard/recent-activities', {
      params: { limit }
    });
    return response.data.activities;
  }
};

export default dashboardService;
