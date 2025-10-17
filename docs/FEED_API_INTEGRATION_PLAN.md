# Feed API 統合計画 - eBay トレンドリサーチツール

このドキュメントは、Feed APIをこのアプリケーションに統合する具体的な計画と実装方法をまとめたものです。

---

## 📋 Feed APIの概要

### Feed APIとは？

eBay Feed APIは、**大量のデータを一括取得・更新するための非同期API**です。

**主な特徴**:
- ⚡ **高速**: Trading APIの10-100倍の速度
- 📦 **バルク処理**: 1リクエストで数千件のデータを取得
- 🔄 **非同期処理**: タスクベースのワークフロー
- 💾 **ファイルベース**: CSV/JSON/XMLフォーマット

---

## 🎯 このアプリケーションでの活用方法

### 現在の課題

**Trading API（現在使用中）**:
- ❌ **遅い**: 4,311アイテム = 4,311コール（約9時間実行）
- ❌ **API制限**: 5,000コール/日（86.6%使用）
- ❌ **スケーラビリティ**: 5,000アイテム以上で制限超過

**Feed API（提案）**:
- ✅ **高速**: 4,311アイテム = 1-2コールで取得可能
- ✅ **効率的**: 100,000コール/日の余裕
- ✅ **スケーラブル**: 数万アイテムでも対応可能

---

## 🚀 統合シナリオ

### シナリオ1: 初回同期（最優先）

**目的**: 新規アカウント接続時の高速データ取得

**従来の方法（Trading API）**:
```
1. GetMyeBaySelling (1コール) → アイテムID一覧取得
2. GetItem × 4,311回 (4,311コール) → 各アイテムの詳細取得
---
合計: 4,312コール、約9時間
```

**Feed API活用後**:
```
1. createTask (LMS_ACTIVE_INVENTORY_REPORT) → タスク作成
2. getTask (ポーリング) → ステータス確認
3. downloadResultFile → CSVファイル一括ダウンロード
---
合計: 3コール、約5-10分
```

**削減効果**:
- APIコール数: **4,312 → 3コール**（99.9%削減）
- 実行時間: **9時間 → 10分**（98%削減）

---

### シナリオ2: 日次差分更新（推奨）

**目的**: 毎日の定期同期を効率化

**ハイブリッドアプローチ**:

```
1. 月初（1日）: Feed API でフル同期
   - LMS_ACTIVE_INVENTORY_REPORT で全アイテム取得
   - 4,311アイテム = 3コール

2. 日次（2-30日）: Trading API で差分更新
   - 変更があったアイテムのみ取得
   - 推定100-200アイテム/日 = 100-200コール
```

**削減効果**:
- 月間APIコール数: **129,360 → 3,000コール**（97.7%削減）
  - 従来: 4,312コール × 30日 = 129,360コール
  - Feed活用後: 3コール + (200コール × 30日) = 6,003コール

---

### シナリオ3: Watch数の補完（現在不可、将来対応）

**問題点**:
- Feed API (`LMS_ACTIVE_INVENTORY_REPORT`) には **Watch数が含まれない**
- Watch数はTrading APIでのみ取得可能

**対処法**:
1. **基本データ**: Feed APIで取得（item_id, title, price, quantity等）
2. **Watch数のみ**: Trading APIで取得（差分のみ）

```python
# Feed APIで基本データ取得
feed_data = download_active_inventory_report()
save_to_database(feed_data)  # 4,311アイテム保存

# Watch数が必要なアイテムのみTrading APIで取得
trending_items = get_items_with_high_view_growth()  # 上位100件
for item in trending_items:
    watch_count = trading_api.get_item(item.item_id).watch_count
    update_watch_count(item, watch_count)
```

**削減効果**:
- APIコール数: **4,312 → 103コール**（97.6%削減）
  - Feed API: 3コール（全アイテム基本データ）
  - Trading API: 100コール（トレンドアイテムのみWatch数）

---

## 📊 Feed API データ構造

### LMS_ACTIVE_INVENTORY_REPORT の内容

Feed APIで取得できるデータ:

| フィールド | Feed API | Trading API | 備考 |
|-----------|----------|-------------|------|
| item_id (SKU) | ✅ | ✅ | |
| title | ✅ | ✅ | |
| price | ✅ | ✅ | |
| quantity | ✅ | ✅ | |
| category | ✅ | ✅ | |
| listing_status | ✅ | ✅ | |
| start_time | ✅ | ✅ | |
| end_time | ✅ | ✅ | |
| **watch_count** | ❌ | ✅ | Trading APIのみ |
| **view_count (HitCount)** | ❌ | ❌ | Analytics APIで取得 |

**結論**: Feed APIは基本データ取得に最適、Watch数はTrading API併用が必要

---

## 🔧 実装計画

### Phase 1: Feed API Client実装

**ファイル**: `backend/app/clients/feed_api_client.py`

```python
class FeedAPIClient(EbayClientBase):
    """eBay Feed API Client for bulk data operations"""

    def create_inventory_task(self, access_token: str) -> str:
        """
        Create active inventory report task

        Returns:
            task_id: Task identifier for monitoring
        """
        url = f"{self.base_url}/sell/feed/v1/task"
        payload = {
            "schemaVersion": "1.0",
            "feedType": "LMS_ACTIVE_INVENTORY_REPORT"
        }
        response = self._make_request('POST', url, headers=headers, json=payload)
        task_id = response.headers['Location'].split('/')[-1]
        return task_id

    def get_task_status(self, task_id: str, access_token: str) -> dict:
        """
        Get task status (QUEUED, PROCESSING, COMPLETED, FAILED)

        Returns:
            {
                'status': 'COMPLETED',
                'feedType': 'LMS_ACTIVE_INVENTORY_REPORT',
                'resultHref': 'https://...',
                'creationDate': '2025-10-17T00:00:00Z',
                'completionDate': '2025-10-17T00:05:00Z'
            }
        """
        url = f"{self.base_url}/sell/feed/v1/task/{task_id}"
        return self._make_request('GET', url, headers=headers).json()

    def download_result_file(self, result_href: str, access_token: str) -> bytes:
        """
        Download result file (CSV/JSON compressed)

        Returns:
            Compressed file content (csv.gz)
        """
        response = self._make_request('GET', result_href, headers=headers)
        return response.content

    def parse_inventory_report(self, csv_content: bytes) -> List[dict]:
        """
        Parse CSV inventory report

        Returns:
            [
                {
                    'sku': 'item123',
                    'title': 'Product Name',
                    'price': 99.99,
                    'quantity': 5,
                    ...
                },
                ...
            ]
        """
        import gzip
        import csv
        from io import StringIO

        # Decompress
        decompressed = gzip.decompress(csv_content).decode('utf-8')

        # Parse CSV
        reader = csv.DictReader(StringIO(decompressed))
        return [row for row in reader]
```

---

### Phase 2: Celeryタスク実装

**ファイル**: `backend/app/tasks/feed_sync.py`

```python
@celery.task(bind=True, max_retries=3)
def sync_account_with_feed_api(self, account_id: str):
    """
    Sync account data using Feed API (fast bulk sync)

    Workflow:
        1. Create inventory report task
        2. Poll task status until COMPLETED
        3. Download result file
        4. Parse and save to database
    """
    db = SessionLocal()

    try:
        account = db.query(EbayAccount).get(account_id)
        feed_client = FeedAPIClient()

        # Step 1: Create task
        logger.info(f"Creating inventory report task for {account.username}")
        task_id = feed_client.create_inventory_task(account.credential.access_token)

        # Step 2: Poll status (max 10 minutes)
        max_attempts = 60  # 10 minutes (every 10 seconds)
        for attempt in range(max_attempts):
            task_status = feed_client.get_task_status(task_id, account.credential.access_token)

            if task_status['status'] == 'COMPLETED':
                logger.info(f"Task completed: {task_id}")
                break
            elif task_status['status'] == 'FAILED':
                raise Exception(f"Task failed: {task_status.get('message')}")

            time.sleep(10)  # Wait 10 seconds

        # Step 3: Download result
        result_href = task_status['resultHref']
        csv_content = feed_client.download_result_file(result_href, account.credential.access_token)

        # Step 4: Parse and save
        inventory_data = feed_client.parse_inventory_report(csv_content)

        saved_count = 0
        for item_data in inventory_data:
            # Save to listings table
            listing = db.query(Listing).filter_by(
                account_id=account_id,
                item_id=item_data['sku']
            ).first()

            if not listing:
                listing = Listing(
                    account_id=account_id,
                    item_id=item_data['sku']
                )
                db.add(listing)

            # Update fields
            listing.title = item_data['title']
            listing.price = float(item_data['price'])
            listing.quantity = int(item_data['quantity'])
            # ... other fields

            db.commit()
            saved_count += 1

        logger.info(f"Saved {saved_count} listings from Feed API")

        return {
            'status': 'success',
            'items_synced': saved_count
        }

    except Exception as exc:
        logger.error(f"Feed sync failed: {exc}")
        db.rollback()
        raise self.retry(exc=exc, countdown=300)

    finally:
        db.close()
```

---

### Phase 3: ハイブリッド同期戦略

**ファイル**: `backend/app/tasks/hybrid_sync.py`

```python
@celery.task
def smart_sync_all_accounts():
    """
    Smart hybrid sync strategy:
    - Day 1 of month: Feed API (full sync)
    - Day 2-30: Trading API (differential sync)
    """
    db = SessionLocal()

    try:
        today = datetime.utcnow().day
        accounts = db.query(EbayAccount).filter_by(is_active=True).all()

        for account in accounts:
            if today == 1:
                # Monthly full sync with Feed API
                logger.info(f"Monthly full sync for {account.username} (Feed API)")
                sync_account_with_feed_api.delay(account.id)
            else:
                # Daily differential sync with Trading API
                logger.info(f"Daily differential sync for {account.username} (Trading API)")
                sync_account_differential.delay(account.id)

    finally:
        db.close()

@celery.task
def sync_account_differential(account_id: str):
    """
    Differential sync: only fetch items with recent changes

    Strategy:
        1. Get all item IDs from database
        2. Check last_modified_time from GetMyeBaySelling
        3. Only fetch items modified since last sync
    """
    db = SessionLocal()

    try:
        account = db.query(EbayAccount).get(account_id)
        trading_client = TradingAPIClient()

        # Get last sync time
        last_sync = account.last_sync_at or (datetime.utcnow() - timedelta(days=1))

        # Get modified items only
        modified_items = trading_client.get_modified_items_since(
            access_token=account.credential.access_token,
            modified_since=last_sync
        )

        logger.info(f"Found {len(modified_items)} modified items")

        # Fetch details only for modified items
        for item_id in modified_items:
            item_data = trading_client.get_item(item_id, account.credential.access_token)
            save_listing_data(db, account, item_data)

        # Update last sync time
        account.last_sync_at = datetime.utcnow()
        db.commit()

        return {
            'status': 'success',
            'items_synced': len(modified_items)
        }

    finally:
        db.close()
```

---

## 📈 期待される効果

### API使用量の削減

| 同期タイプ | 従来（Trading API） | Feed API活用後 | 削減率 |
|-----------|-------------------|----------------|--------|
| 初回同期 | 4,312コール | 3コール | 99.9% |
| 月次フル同期 | 4,312コール | 3コール | 99.9% |
| 日次差分同期 | 4,312コール | 100-200コール | 95-97% |
| **月間合計** | **129,360コール** | **6,003コール** | **95.4%** |

### 実行時間の短縮

| 同期タイプ | 従来 | Feed API活用後 | 短縮率 |
|-----------|------|---------------|--------|
| 初回同期 | 9時間 | 10分 | 98% |
| 月次フル同期 | 9時間 | 10分 | 98% |
| 日次差分同期 | 9時間 | 5-10分 | 98% |

### スケーラビリティの向上

| アイテム数 | Trading APIのみ | Feed API活用 | 対応可能 |
|-----------|----------------|-------------|---------|
| 5,000件 | ❌ リミット超過 | ✅ 3コール | 可能 |
| 10,000件 | ❌ 大幅超過 | ✅ 3コール | 可能 |
| 50,000件 | ❌ 不可能 | ✅ 3コール | 可能 |
| 100,000件 | ❌ 不可能 | ✅ 3コール | 可能 |

---

## ⚠️ 注意事項と制約

### 1. Watch数の取得

**問題**: Feed APIにはWatch数が含まれない

**解決策**:
- オプション1: トレンド商品（上位100件）のみTrading APIでWatch数取得
- オプション2: Watch数なしでトレンド分析（View数とPrice成長率のみ）
- オプション3: 週次でWatch数をバッチ更新

### 2. View数の取得

**問題**: Feed APIにもTrading APIにもView数（HitCount）が含まれない

**解決策**:
- Analytics APIで継続取得（現在の実装のまま）

### 3. OAuth スコープ

**必要なスコープ**:
```
https://api.ebay.com/oauth/api_scope/sell.inventory
https://api.ebay.com/oauth/api_scope/sell.inventory.readonly
```

**確認方法**:
```python
# 現在のOAuth認証情報のスコープを確認
credential = db.query(OAuthCredential).first()
print(credential.scopes)  # 'sell.inventory'が含まれているか確認
```

### 4. ファイル保持期間

- **LMS_ACTIVE_INVENTORY_REPORT**: 90日間
- タスク完了後、90日以内にダウンロード必要

### 5. タスク処理時間

- 通常: 5-10分
- 大量データ（10,000+アイテム）: 最大30分
- タイムアウト対策: 最大60分待機

---

## 🎯 実装の優先順位

### Phase 1: Feed API Client実装（最優先）
- **工数**: 2-3日
- **効果**: 初回同期を9時間 → 10分に短縮
- **リスク**: 低

### Phase 2: 初回同期への統合
- **工数**: 1-2日
- **効果**: 新規アカウント接続時の高速化
- **リスク**: 低

### Phase 3: ハイブリッド同期戦略
- **工数**: 3-4日
- **効果**: 月間API使用量95%削減
- **リスク**: 中（差分検出ロジックの実装必要）

### Phase 4: Watch数補完ロジック
- **工数**: 2日
- **効果**: トレンド分析の精度向上
- **リスク**: 低

---

## 🔗 関連リソース

- [Feed API公式ドキュメント](https://developer.ebay.com/api-docs/sell/feed/overview.html)
- [LMS_ACTIVE_INVENTORY_REPORT仕様](https://developer.ebay.com/api-docs/sell/feed/types/api:FeedTypeEnum)
- [Feed API Playground](https://developer.ebay.com/my/api-test-tool)
- [OAuth Scopes](https://developer.ebay.com/api-docs/static/oauth-scopes.html)

---

**Last Updated**: 2025-10-17
**Status**: 設計完了、実装待ち
**推奨**: Phase 1を最優先で実装（初回同期の高速化）
