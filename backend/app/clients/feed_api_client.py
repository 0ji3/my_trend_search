"""
eBay Feed API Client

大量の出品データを一括取得するためのFeed API
初回同期時の高速化に使用
"""
import logging
import os
from typing import Dict, Any, Optional, List
from datetime import datetime
import random
import gzip
import json

from app.clients.ebay_client_base import EbayClientBase

logger = logging.getLogger(__name__)


class FeedAPIClient(EbayClientBase):
    """
    eBay Feed API Client

    Item Feed APIを使用して、全出品物データを一括取得
    """

    def __init__(self):
        super().__init__()
        self.base_url = "https://api.ebay.com/sell/feed/v1"

        # サンドボックス環境用URL
        if self.environment == 'sandbox':
            self.base_url = "https://api.sandbox.ebay.com/sell/feed/v1"

    def create_inventory_task(
        self,
        access_token: str,
        feed_type: str = "LMS_ACTIVE_INVENTORY_REPORT",
        marketplace_id: str = "EBAY_US"
    ) -> Dict[str, Any]:
        """
        在庫レポートタスクを作成

        Args:
            access_token: OAuthアクセストークン
            feed_type: フィードタイプ
            marketplace_id: マーケットプレイスID

        Returns:
            dict: タスク情報 (task_id, status, etc.)
        """
        if self._should_use_mock():
            return self._mock_create_inventory_task()

        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

        payload = {
            'feedType': feed_type,
            'schemaVersion': '1.0'
        }

        try:
            response = self._make_request(
                'POST',
                f"{self.base_url}/inventory_task",
                headers=headers,
                json=payload,
                params={'X-EBAY-C-MARKETPLACE-ID': marketplace_id}
            )

            # Location ヘッダーからtask_idを取得
            location = response.headers.get('Location', '')
            task_id = location.split('/')[-1] if location else None

            return {
                'task_id': task_id,
                'status': 'QUEUED',
                'feed_type': feed_type,
                'creation_date': datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to create inventory task: {e}")
            raise

    def get_task_status(
        self,
        access_token: str,
        task_id: str
    ) -> Dict[str, Any]:
        """
        タスクのステータスを確認

        Args:
            access_token: OAuthアクセストークン
            task_id: タスクID

        Returns:
            dict: タスクステータス情報
        """
        if self._should_use_mock():
            return self._mock_get_task_status(task_id)

        headers = {
            'Authorization': f'Bearer {access_token}',
            'Accept': 'application/json'
        }

        try:
            response = self._make_request(
                'GET',
                f"{self.base_url}/task/{task_id}",
                headers=headers
            )

            return response.json()

        except Exception as e:
            logger.error(f"Failed to get task status: {e}")
            raise

    def download_result_file(
        self,
        access_token: str,
        task_id: str
    ) -> List[Dict[str, Any]]:
        """
        結果ファイルをダウンロードして解析

        Args:
            access_token: OAuthアクセストークン
            task_id: タスクID

        Returns:
            List[dict]: 出品物データのリスト
        """
        if self._should_use_mock():
            return self._mock_download_result_file()

        # まずタスクステータスを確認してダウンロードURLを取得
        task_status = self.get_task_status(access_token, task_id)

        if task_status.get('status') != 'COMPLETED':
            raise Exception(f"Task {task_id} is not completed yet. Status: {task_status.get('status')}")

        # 結果ファイルのURLを取得
        result_href = task_status.get('resultHref')
        if not result_href:
            raise Exception(f"No result file available for task {task_id}")

        headers = {
            'Authorization': f'Bearer {access_token}',
            'Accept': 'application/gzip'
        }

        try:
            # gzip形式のファイルをダウンロード
            response = self._make_request(
                'GET',
                result_href,
                headers=headers
            )

            # gzipを解凍してJSONとしてパース
            decompressed_data = gzip.decompress(response.content)
            json_data = json.loads(decompressed_data.decode('utf-8'))

            # JSONファイルは通常、1行1レコード形式（JSONL）
            listings = []
            for line in decompressed_data.decode('utf-8').split('\n'):
                if line.strip():
                    listings.append(json.loads(line))

            logger.info(f"Downloaded {len(listings)} listings from Feed API")
            return listings

        except Exception as e:
            logger.error(f"Failed to download result file: {e}")
            raise

    def get_inventory_feed(
        self,
        access_token: str,
        marketplace_id: str = "EBAY_US",
        wait_for_completion: bool = False,
        max_wait_seconds: int = 300
    ) -> List[Dict[str, Any]]:
        """
        在庫フィードを取得（タスク作成→待機→ダウンロード）

        Args:
            access_token: OAuthアクセストークン
            marketplace_id: マーケットプレイスID
            wait_for_completion: 完了まで待機するか
            max_wait_seconds: 最大待機時間（秒）

        Returns:
            List[dict]: 出品物データのリスト
        """
        if self._should_use_mock():
            return self._mock_download_result_file()

        # タスクを作成
        task_info = self.create_inventory_task(access_token, marketplace_id=marketplace_id)
        task_id = task_info['task_id']

        logger.info(f"Created inventory task: {task_id}")

        if not wait_for_completion:
            return []  # タスクIDのみ返して、後で取得

        # タスク完了を待機
        import time
        elapsed = 0
        interval = 10  # 10秒ごとにチェック

        while elapsed < max_wait_seconds:
            time.sleep(interval)
            elapsed += interval

            status_info = self.get_task_status(access_token, task_id)
            status = status_info.get('status')

            logger.info(f"Task {task_id} status: {status}")

            if status == 'COMPLETED':
                # ダウンロード
                return self.download_result_file(access_token, task_id)
            elif status in ['FAILED', 'FATAL_ERROR']:
                raise Exception(f"Task {task_id} failed with status: {status}")

        raise Exception(f"Task {task_id} did not complete within {max_wait_seconds} seconds")

    # ================== Mock Data Generation ==================

    def _mock_create_inventory_task(self) -> Dict[str, Any]:
        """
        モック在庫タスクを作成

        Returns:
            dict: モックタスク情報
        """
        logger.info("[MOCK] Creating inventory task")

        task_id = f"task_mock_{int(datetime.now().timestamp())}"

        return {
            'task_id': task_id,
            'status': 'COMPLETED',  # モックなので即完了
            'feed_type': 'LMS_ACTIVE_INVENTORY_REPORT',
            'creation_date': datetime.utcnow().isoformat()
        }

    def _mock_get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        モックタスクステータスを返す

        Args:
            task_id: タスクID

        Returns:
            dict: モックタスクステータス
        """
        logger.info(f"[MOCK] Getting task status: {task_id}")

        return {
            'taskId': task_id,
            'status': 'COMPLETED',
            'feedType': 'LMS_ACTIVE_INVENTORY_REPORT',
            'creationDate': datetime.utcnow().isoformat(),
            'completionDate': datetime.utcnow().isoformat(),
            'resultHref': f'https://mock.ebay.com/result/{task_id}'
        }

    def _mock_download_result_file(self) -> List[Dict[str, Any]]:
        """
        モック結果ファイルを生成

        Returns:
            List[dict]: モック出品物データ
        """
        logger.info("[MOCK] Generating mock inventory data (50 listings)")

        listings = []
        for i in range(50):
            item_id = f"1100{str(i).zfill(8)}"

            listings.append({
                'sku': f'SKU-{i:04d}',
                'itemId': item_id,
                'title': f'Mock Product {i} - Premium Quality Item',
                'price': {
                    'value': str(round(random.uniform(10.0, 500.0), 2)),
                    'currency': 'USD'
                },
                'quantity': random.randint(1, 100),
                'quantitySold': random.randint(0, 50),
                'categoryId': str(random.choice([1234, 5678, 9012, 3456])),
                'categoryName': random.choice(['Electronics', 'Fashion', 'Home & Garden', 'Sports']),
                'condition': 'NEW',
                'listingStatus': 'ACTIVE',
                'listingType': 'FIXED_PRICE',
                'imageUrls': [
                    f'https://i.ebayimg.com/images/mock/{item_id}_1.jpg'
                ],
                'itemSpecifics': {
                    'Brand': random.choice(['Brand A', 'Brand B', 'Brand C']),
                    'Model': f'Model-{i}',
                    'Color': random.choice(['Black', 'White', 'Blue', 'Red'])
                }
            })

        return listings
