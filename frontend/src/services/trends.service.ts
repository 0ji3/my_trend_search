/**
 * Trends API Service
 *
 * トレンド分析データを取得
 */
import api from './api';

export interface TrendAnalysis {
  id: string;
  listing_id: string;
  analysis_date: string;
  view_growth_rate: number | null;
  watch_growth_rate: number | null;
  view_7day_avg: number | null;
  watch_7day_avg: number | null;
  trend_score: number;
  rank: number | null;
  is_trending: boolean;
  created_at: string;
  // Listing information
  item_id: string;
  title: string;
  price: number | null;
  currency: string;
  image_url: string | null;
  category_name: string | null;
}

export interface TopTrendingResponse {
  analysis_date: string;
  total_count: number;
  trends: TrendAnalysis[];
}

const trendsService = {
  /**
   * TOP Nトレンド商品を取得
   * @param limit 取得件数（デフォルト10件）
   * @param analysisDate 分析対象日（未指定の場合は最新）
   */
  getTopTrending: async (
    limit: number = 10,
    analysisDate?: string
  ): Promise<TopTrendingResponse> => {
    const response = await api.get<TopTrendingResponse>('/trends/top', {
      params: {
        limit,
        ...(analysisDate && { analysis_date: analysisDate })
      }
    });
    return response.data;
  },

  /**
   * 特定商品のトレンド履歴を取得
   * @param listingId 出品物ID
   * @param startDate 開始日（未指定の場合は7日前）
   * @param endDate 終了日（未指定の場合は今日）
   */
  getListingHistory: async (
    listingId: string,
    startDate?: string,
    endDate?: string
  ): Promise<any> => {
    const response = await api.get(`/trends/listing/${listingId}/history`, {
      params: {
        ...(startDate && { start_date: startDate }),
        ...(endDate && { end_date: endDate })
      }
    });
    return response.data;
  },

  /**
   * トレンド分析を手動トリガー
   * @param accountId 特定アカウントのみ分析（未指定の場合は全アカウント）
   * @param analysisDate 分析対象日（未指定の場合は今日）
   */
  triggerAnalysis: async (
    accountId?: string,
    analysisDate?: string
  ): Promise<{ status: string; task_id: string; message: string }> => {
    const response = await api.post('/trends/analyze', {
      ...(accountId && { account_id: accountId }),
      ...(analysisDate && { analysis_date: analysisDate })
    });
    return response.data;
  },

  /**
   * 利用可能な分析日一覧を取得
   * @param limit 取得件数（デフォルト30日分）
   */
  getAnalysisDates: async (limit: number = 30): Promise<string[]> => {
    const response = await api.get<string[]>('/trends/analysis-dates', {
      params: { limit }
    });
    return response.data;
  }
};

export default trendsService;
