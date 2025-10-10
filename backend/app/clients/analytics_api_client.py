"""
eBay Analytics API Client

トラフィックレポートなどの詳細な分析データを取得
"""
import logging
import os
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import random

from app.clients.ebay_client_base import EbayClientBase

logger = logging.getLogger(__name__)


class AnalyticsAPIClient(EbayClientBase):
    """
    eBay Analytics API Client

    Traffic Report APIを使用して、出品物の詳細なトラフィックデータを取得
    """

    def __init__(self):
        super().__init__()
        self.base_url = "https://api.ebay.com/sell/analytics/v1"

        # サンドボックス環境用URL
        if self.environment == 'sandbox':
            self.base_url = "https://api.sandbox.ebay.com/sell/analytics/v1"

    def get_traffic_report(
        self,
        access_token: str,
        dimension: str = "LISTING",
        metric: str = "CLICK_THROUGH_RATE,LISTING_IMPRESSION,LISTING_VIEWS",
        filter_params: Optional[Dict[str, str]] = None,
        sort: Optional[str] = None,
        limit: int = 200,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        トラフィックレポートを取得

        Args:
            access_token: OAuthアクセストークン
            dimension: レポートの次元 (LISTING, DAY, etc.)
            metric: 取得するメトリクス (カンマ区切り)
            filter_params: フィルター条件
            sort: ソート条件
            limit: 取得件数
            offset: オフセット

        Returns:
            dict: トラフィックレポートデータ
        """
        if self._should_use_mock():
            return self._mock_get_traffic_report(limit)

        # クエリパラメータを構築
        params = {
            'dimension': dimension,
            'metric': metric,
            'limit': limit,
            'offset': offset
        }

        if filter_params:
            # フィルター形式: listingIds:{item_id1|item_id2}
            params['filter'] = ','.join([f"{k}:{v}" for k, v in filter_params.items()])

        if sort:
            params['sort'] = sort

        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

        try:
            response = self._make_request(
                'GET',
                f"{self.base_url}/traffic_report",
                headers=headers,
                params=params
            )

            return response.json()

        except Exception as e:
            logger.error(f"Failed to get traffic report: {e}")
            raise

    def get_listing_traffic(
        self,
        access_token: str,
        listing_ids: List[str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        特定の出品物のトラフィックデータを取得

        Args:
            access_token: OAuthアクセストークン
            listing_ids: 出品物IDリスト
            start_date: 開始日 (YYYY-MM-DD)
            end_date: 終了日 (YYYY-MM-DD)

        Returns:
            dict: 出品物別トラフィックデータ
        """
        if self._should_use_mock():
            return self._mock_get_listing_traffic(listing_ids)

        # フィルター条件を構築
        filter_params = {}

        if listing_ids:
            # 最大50件まで
            ids_str = '|'.join(listing_ids[:50])
            filter_params['listingIds'] = f"{{{ids_str}}}"

        if start_date and end_date:
            filter_params['lastAccessedDate'] = f"[{start_date}..{end_date}]"

        return self.get_traffic_report(
            access_token=access_token,
            dimension="LISTING",
            metric="CLICK_THROUGH_RATE,LISTING_IMPRESSION,LISTING_VIEWS,SALES_CONVERSION_RATE",
            filter_params=filter_params
        )

    # ================== Mock Data Generation ==================

    def _mock_get_traffic_report(self, limit: int) -> Dict[str, Any]:
        """
        モックトラフィックレポートを生成

        Args:
            limit: 取得件数

        Returns:
            dict: モックトラフィックレポート
        """
        logger.info(f"[MOCK] Generating traffic report with {limit} records")

        records = []
        for i in range(min(limit, 50)):
            item_id = f"1100{str(i).zfill(8)}"

            records.append({
                'dimensionValues': [
                    {
                        'dimension': 'LISTING',
                        'value': item_id
                    }
                ],
                'metricValues': [
                    {
                        'metric': 'CLICK_THROUGH_RATE',
                        'value': str(round(random.uniform(1.0, 8.0), 2))
                    },
                    {
                        'metric': 'LISTING_IMPRESSION',
                        'value': str(random.randint(500, 5000))
                    },
                    {
                        'metric': 'LISTING_VIEWS',
                        'value': str(random.randint(100, 1000))
                    },
                    {
                        'metric': 'SALES_CONVERSION_RATE',
                        'value': str(round(random.uniform(0.5, 5.0), 2))
                    }
                ]
            })

        return {
            'dimensionMetadata': [
                {
                    'dimension': 'LISTING',
                    'dataType': 'STRING'
                }
            ],
            'metricMetadata': [
                {
                    'metric': 'CLICK_THROUGH_RATE',
                    'dataType': 'PERCENTAGE'
                },
                {
                    'metric': 'LISTING_IMPRESSION',
                    'dataType': 'INTEGER'
                },
                {
                    'metric': 'LISTING_VIEWS',
                    'dataType': 'INTEGER'
                },
                {
                    'metric': 'SALES_CONVERSION_RATE',
                    'dataType': 'PERCENTAGE'
                }
            ],
            'records': records,
            'total': len(records),
            'href': '/sell/analytics/v1/traffic_report',
            'limit': limit,
            'offset': 0
        }

    def _mock_get_listing_traffic(self, listing_ids: List[str]) -> Dict[str, Any]:
        """
        モック出品物トラフィックデータを生成

        Args:
            listing_ids: 出品物IDリスト

        Returns:
            dict: モック出品物トラフィックデータ
        """
        logger.info(f"[MOCK] Generating listing traffic for {len(listing_ids)} listings")

        records = []
        for item_id in listing_ids[:50]:
            records.append({
                'dimensionValues': [
                    {
                        'dimension': 'LISTING',
                        'value': item_id
                    }
                ],
                'metricValues': [
                    {
                        'metric': 'CLICK_THROUGH_RATE',
                        'value': str(round(random.uniform(1.0, 8.0), 2))
                    },
                    {
                        'metric': 'LISTING_IMPRESSION',
                        'value': str(random.randint(500, 5000))
                    },
                    {
                        'metric': 'LISTING_VIEWS',
                        'value': str(random.randint(100, 1000))
                    },
                    {
                        'metric': 'SALES_CONVERSION_RATE',
                        'value': str(round(random.uniform(0.5, 5.0), 2))
                    }
                ]
            })

        return {
            'dimensionMetadata': [
                {
                    'dimension': 'LISTING',
                    'dataType': 'STRING'
                }
            ],
            'metricMetadata': [
                {
                    'metric': 'CLICK_THROUGH_RATE',
                    'dataType': 'PERCENTAGE'
                },
                {
                    'metric': 'LISTING_IMPRESSION',
                    'dataType': 'INTEGER'
                },
                {
                    'metric': 'LISTING_VIEWS',
                    'dataType': 'INTEGER'
                },
                {
                    'metric': 'SALES_CONVERSION_RATE',
                    'dataType': 'PERCENTAGE'
                }
            ],
            'records': records,
            'total': len(records)
        }
