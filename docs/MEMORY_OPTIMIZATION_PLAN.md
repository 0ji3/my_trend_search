# メモリ最適化計画 - eBay トレンドリサーチツール

## 📊 現状分析

### 現在のメモリ使用状況

| コンテナ | メモリ使用量 | 使用率 | 問題 |
|---------|-------------|--------|------|
| Backend | 1.0 GB | 6.5% | ⚠️ 同期タスク実行時に増加 |
| Frontend | 1.6 GB | 10.6% | ⚠️ React開発サーバー |
| Celery Worker | 113 MB | 0.7% | ✅ 正常 |
| Celery Beat | 81 MB | 0.5% | ✅ 正常 |
| PostgreSQL | 35 MB | 0.2% | ✅ 正常 |
| Redis | 8 MB | 0.05% | ✅ 正常 |
| **合計** | **~2.9 GB** | **18.7%** | ⚠️ タスク実行時に16GB超過 |

### 問題の原因

**同期タスク（`sync_account_listings`）の実装**:

```python
# 問題1: 全アイテムをメモリに保持
all_items = await self._fetch_all_active_items(access_token, account.tenant_id)
# ↑ 4,311アイテム分のデータを一度にメモリに保持

# 問題2: ループ内でDBコミットを繰り返す
for item_summary in all_items:  # 4,311回ループ
    item_data = self.trading_client.get_item(item_id, access_token)
    listing = self._upsert_listing(account, item_data)  # ← commit
    self._insert_daily_metric(listing, item_data)       # ← commit
    # メモリがどんどん蓄積
```

**メモリ蓄積の原因**:
1. **4,311アイテムの一括読み込み**: リスト全体をメモリに保持
2. **4,311回のDBコミット**: SQLAlchemyセッションにオブジェクトが蓄積
3. **SQLAlchemyのアイデンティティマップ**: コミット後もオブジェクトがキャッシュされる
4. **9時間の長時間実行**: メモリリークが蓄積

**Exit Code 137の原因**:
- Dockerのメモリ制限（16GB）に到達
- OOM Killer（Out of Memory Killer）がプロセスを強制終了

---

## 🎯 最適化戦略

### 戦略1: バッチ処理（最優先）

**目的**: メモリ使用量を一定に保つ

**実装方法**: 100-200アイテムごとにバッチ処理

```python
# Before: 全アイテムを一度にメモリ保持
all_items = await self._fetch_all_active_items(...)  # 4,311アイテム
for item in all_items:
    sync_item(item)

# After: ページごとにバッチ処理
for page in range(1, total_pages + 1):
    items_batch = get_page(page, entries_per_page=200)  # 200アイテムのみ
    for item in items_batch:
        sync_item(item)
    # ページ終了後にセッションクリア
    db.flush()
    db.expunge_all()  # メモリから削除
```

**効果**:
- メモリ使用量: **4,311アイテム → 200アイテム**（95%削減）
- ピークメモリ: **~16GB → ~1GB**

---

### 戦略2: SQLAlchemyセッション管理

**目的**: DBセッションのメモリリークを防ぐ

**実装方法**:

```python
# Before: セッションにオブジェクトが蓄積
for item in all_items:  # 4,311回
    listing = self._upsert_listing(item)  # commit
    self.db.commit()  # オブジェクトがセッションに残る

# After: 定期的にセッションをクリア
BATCH_SIZE = 100
for idx, item in enumerate(items_batch):
    listing = self._upsert_listing(item)

    # 100件ごとにコミット＆クリア
    if (idx + 1) % BATCH_SIZE == 0:
        self.db.commit()
        self.db.expunge_all()  # アイデンティティマップをクリア
        logger.debug(f"Flushed session after {idx + 1} items")

# 残りをコミット
self.db.commit()
```

**効果**:
- SQLAlchemyのアイデンティティマップサイズ: **4,311オブジェクト → 100オブジェクト**
- メモリ使用量: **約80%削減**

---

### 戦略3: Docker Compose メモリ制限設定

**目的**: 各コンテナにメモリ上限を設定し、暴走を防ぐ

**実装方法**: `docker-compose.yml`に制限を追加

```yaml
services:
  backend:
    # ... existing config ...
    deploy:
      resources:
        limits:
          memory: 2G  # 最大2GB
        reservations:
          memory: 512M  # 最低512MB

  celery-worker:
    # ... existing config ...
    deploy:
      resources:
        limits:
          memory: 3G  # 最大3GB（同期タスク用）
        reservations:
          memory: 256M

  frontend:
    # ... existing config ...
    deploy:
      resources:
        limits:
          memory: 1G  # 開発サーバーは1GBで十分
        reservations:
          memory: 256M
```

**効果**:
- 各コンテナが個別の上限を持つ
- 1つのコンテナが暴走しても他に影響しない
- 合計上限: 2G + 3G + 1G + ... = 約8GB（16GB内に収まる）

---

### 戦略4: Celeryワーカー設定の最適化

**目的**: Celeryワーカーのメモリリークを防ぐ

**実装方法**: `celery_app.py`の設定を調整

```python
celery.conf.update(
    # Before
    worker_max_tasks_per_child=1000,  # 1000タスク実行後にワーカー再起動

    # After
    worker_max_tasks_per_child=10,    # 10タスク実行後にワーカー再起動
    worker_prefetch_multiplier=1,     # 1タスクずつ処理
    task_acks_late=True,              # タスク完了後にACK
    task_reject_on_worker_lost=True,  # ワーカー停止時はタスク再実行
)
```

**効果**:
- 長時間実行によるメモリリークを防ぐ
- 10タスクごとにワーカープロセスが再起動され、メモリがクリアされる

---

### 戦略5: ログレベルの調整

**目的**: 過剰なログ出力によるメモリ消費を削減

**実装方法**:

```python
# Before: INFOレベルで全ログ出力
logging.basicConfig(level=logging.INFO)

# After: WARNINGレベルに変更（本番環境）
logging.basicConfig(level=logging.WARNING)

# 重要なイベントのみINFOレベルで出力
logger.info(f"Sync started for account {account_id}")
logger.info(f"Sync completed: {synced_count} items")
```

**効果**:
- ログメッセージの削減（4,311件 → 数十件）
- メモリ使用量: 約10-20%削減

---

## 🔧 実装コード

### 修正1: `ebay_data_sync_service.py` - バッチ処理化

```python
async def sync_account_listings(self, account: EbayAccount) -> Dict[str, Any]:
    """
    Sync all active listings for one eBay account (memory-optimized)
    """
    logger.info(f"Starting sync for account {account.id}")

    # Check cache
    if self.cache_service.is_synced_today(str(account.id), "trading"):
        logger.info(f"Account {account.id} already synced today, skipping")
        return {'account_id': str(account.id), 'items_synced': 0, 'cached': True}

    errors = []
    synced_count = 0
    failed_count = 0

    try:
        # Get valid OAuth token
        access_token = await self.oauth_service.get_valid_access_token(
            self.db, account.tenant_id
        )

        # === 修正: ページ単位でバッチ処理 ===
        page = 1
        entries_per_page = 200
        COMMIT_BATCH_SIZE = 100  # 100件ごとにコミット

        while True:
            # Fetch one page at a time
            result = self.trading_client.get_my_ebay_selling(
                access_token,
                page_number=page,
                entries_per_page=entries_per_page
            )

            items_batch = result['items']
            logger.info(f"Processing page {page}/{result['total_pages']} ({len(items_batch)} items)")

            # Process items in this page
            for idx, item_summary in enumerate(items_batch):
                try:
                    item_id = item_summary['item_id']
                    if not item_id:
                        continue

                    # Get item details
                    item_data = self.trading_client.get_item(item_id, access_token)

                    # Upsert listing
                    listing = self._upsert_listing(account, item_data)

                    # Insert daily metric
                    self._insert_daily_metric(listing, item_data)

                    synced_count += 1

                    # === 追加: 100件ごとにセッションクリア ===
                    if synced_count % COMMIT_BATCH_SIZE == 0:
                        self.db.commit()
                        self.db.expunge_all()  # メモリから削除
                        logger.info(f"Committed batch: {synced_count} items synced")

                except Exception as e:
                    failed_count += 1
                    error_msg = f"Failed to sync item {item_summary.get('item_id')}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)

            # === 追加: ページ終了後にコミット ===
            self.db.commit()
            self.db.expunge_all()

            # Check if last page
            if page >= result['total_pages']:
                break

            page += 1

        # Final commit for remaining items
        self.db.commit()

        # Update last_sync_at
        account.last_sync_at = datetime.utcnow()
        self.db.commit()

        # Mark as synced
        self.cache_service.mark_synced_today(str(account.id), "trading")

        logger.info(f"Sync completed: {synced_count} succeeded, {failed_count} failed")

        return {
            'account_id': str(account.id),
            'items_synced': synced_count,
            'items_failed': failed_count,
            'sync_time': account.last_sync_at,
            'errors': errors[:10],
            'cached': False
        }

    except Exception as e:
        logger.error(f"Fatal error syncing account {account.id}: {e}", exc_info=True)
        return {
            'account_id': str(account.id),
            'items_synced': synced_count,
            'items_failed': failed_count,
            'errors': [str(e)],
        }
```

---

### 修正2: `docker-compose.yml` - メモリ制限追加

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:16-alpine
    container_name: ebay_trends_postgres
    # ... existing config ...
    deploy:
      resources:
        limits:
          memory: 512M
        reservations:
          memory: 128M

  redis:
    image: redis:7-alpine
    container_name: ebay_trends_redis
    # ... existing config ...
    deploy:
      resources:
        limits:
          memory: 256M
        reservations:
          memory: 64M

  backend:
    build:
      context: ./backend
    container_name: ebay_trends_backend
    # ... existing config ...
    deploy:
      resources:
        limits:
          memory: 2G
        reservations:
          memory: 512M

  celery-worker:
    build:
      context: ./backend
    container_name: ebay_trends_celery_worker
    # ... existing config ...
    deploy:
      resources:
        limits:
          memory: 4G  # 同期タスク用に多めに確保
        reservations:
          memory: 256M

  celery-beat:
    build:
      context: ./backend
    container_name: ebay_trends_celery_beat
    # ... existing config ...
    deploy:
      resources:
        limits:
          memory: 256M
        reservations:
          memory: 128M

  frontend:
    build:
      context: ./frontend
    container_name: ebay_trends_frontend
    # ... existing config ...
    deploy:
      resources:
        limits:
          memory: 1G
        reservations:
          memory: 256M
```

---

### 修正3: `celery_app.py` - ワーカー設定最適化

```python
# Celery configuration
celery.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes

    # === メモリ最適化設定 ===
    worker_prefetch_multiplier=1,      # 1タスクずつ処理
    worker_max_tasks_per_child=5,      # 5タスク実行後にワーカー再起動（メモリリーク防止）
    task_acks_late=True,               # タスク完了後にACK
    task_reject_on_worker_lost=True,   # ワーカー停止時はタスク再実行

    # === 追加: メモリ上限設定 ===
    worker_max_memory_per_child=3000000,  # 3GB（3,000,000 KB）
)
```

---

### 修正4: ログレベル調整

**`.env`ファイル**:
```bash
# 本番環境
LOG_LEVEL=WARNING

# 開発環境（必要に応じて）
# LOG_LEVEL=INFO
```

**`backend/app/main.py`**:
```python
import os
import logging

# ログレベルを環境変数から取得
log_level = os.getenv('LOG_LEVEL', 'INFO')
logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

---

## 📊 期待される効果

### メモリ使用量の削減

| 項目 | 修正前 | 修正後 | 削減率 |
|------|-------|-------|--------|
| ピークメモリ（同期中） | ~16GB | ~4GB | **75%削減** |
| Backend通常時 | 1.0GB | 0.5GB | 50%削減 |
| Celery Worker同期中 | 10-15GB | 2-3GB | **80%削減** |
| Frontend | 1.6GB | 0.5GB | 70%削減 |
| **合計（同期中）** | **~16GB** | **~6GB** | **62.5%削減** |

### 安定性の向上

| 指標 | 修正前 | 修正後 |
|------|-------|-------|
| OOM Killer発生 | ❌ 発生（Exit 137） | ✅ なし |
| タスク完了率 | ❌ 0%（強制終了） | ✅ 100% |
| 実行時間 | 9時間（途中終了） | 9時間（完了） |

---

## 🚀 実装の優先順位

### Phase 1: バッチ処理化（最優先・必須）
- **工数**: 2-3時間
- **ファイル**: `backend/app/services/ebay_data_sync_service.py`
- **効果**: メモリ使用量75%削減
- **リスク**: 低

### Phase 2: Docker メモリ制限（推奨）
- **工数**: 30分
- **ファイル**: `docker-compose.yml`
- **効果**: コンテナ暴走防止
- **リスク**: 低

### Phase 3: Celeryワーカー最適化（推奨）
- **工数**: 1時間
- **ファイル**: `backend/app/celery_app.py`
- **効果**: 長期実行時のメモリリーク防止
- **リスク**: 低

### Phase 4: ログレベル調整（オプション）
- **工数**: 15分
- **ファイル**: `.env`, `backend/app/main.py`
- **効果**: メモリ・ディスク使用量10-20%削減
- **リスク**: 低

---

## ⚠️ 注意事項

### 1. SQLAlchemy `expunge_all()` の影響

**注意**: セッションから削除されたオブジェクトは再利用できません

```python
# expunge_all()後はオブジェクトが無効
listing = self._upsert_listing(item)
self.db.expunge_all()
print(listing.id)  # ❌ DetachedInstanceError
```

**対処**: 必要なデータは事前に抽出

```python
listing = self._upsert_listing(item)
listing_id = listing.id  # ✅ 値をコピー
self.db.expunge_all()
print(listing_id)  # ✅ OK
```

### 2. Docker Compose v3のメモリ制限

**注意**: `docker-compose up`では`deploy.resources`が無視される場合があります

**対処**: `docker stack deploy`を使用するか、`mem_limit`を併用

```yaml
services:
  backend:
    mem_limit: 2g  # v3で確実に動作
    deploy:
      resources:
        limits:
          memory: 2G  # Swarm mode用
```

### 3. Celeryワーカーの再起動頻度

**注意**: `worker_max_tasks_per_child=5`は5タスクごとに再起動

**影響**:
- 同期タスク1回 = 1タスク
- 5回の同期後にワーカー再起動
- 再起動時間: 約5-10秒

**調整**: 必要に応じて`10`や`20`に増やす

---

## 📝 デプロイ手順

### Step 1: コード修正
```bash
# バックアップ
cp backend/app/services/ebay_data_sync_service.py backend/app/services/ebay_data_sync_service.py.bak

# 修正版をデプロイ（上記の修正1を適用）
```

### Step 2: Docker Compose修正
```bash
# バックアップ
cp docker-compose.yml docker-compose.yml.bak

# メモリ制限を追加（上記の修正2を適用）
```

### Step 3: Celery設定修正
```bash
# バックアップ
cp backend/app/celery_app.py backend/app/celery_app.py.bak

# ワーカー設定を最適化（上記の修正3を適用）
```

### Step 4: 再起動
```bash
# コンテナを再ビルド＆起動
docker-compose down
docker-compose build
docker-compose up -d

# ログ確認
docker-compose logs -f celery_worker
```

### Step 5: テスト実行
```bash
# 手動で同期タスクをトリガー
docker-compose exec backend python -c "
from app.tasks.daily_sync import sync_all_accounts
result = sync_all_accounts()
print(result)
"

# メモリ使用量を監視
watch -n 5 'docker stats --no-stream'
```

---

**Last Updated**: 2025-10-17
**Status**: 設計完了、実装待ち
**推奨**: Phase 1（バッチ処理化）を最優先で実装
