# CLAUDE.md - eBay トレンドリサーチツール 開発ガイド

このドキュメントは、Claude Codeでの開発を円滑に進めるための開発ガイドです。

---

## 📋 プロジェクト概要

### プロジェクト名
**eBay カスタムトレンドリサーチツール**

### 目的
eBay出品者が自身の商品パフォーマンスをモニタリングし、View数やWatch数が急成長している商品（トレンド商品）を自動検出することで、関連商品の出品戦略を最適化するツール。

### 主要機能
1. **マルチアカウント対応**: 複数のeBayアカウントを一元管理
2. **自動データ収集**: 1日1回、全出品物のメトリクスを自動取得（2,000件/アカウント）
3. **トレンド分析**: View数・Watch数の成長率を分析し、TOP10を自動抽出
4. **ダッシュボード**: トレンド商品の可視化とパフォーマンス推移表示
5. **通知機能**: トレンド商品検出時のアラート

---

## 📝 実装状況

### ✅ Phase 1-4: 完了（詳細はREADME.md参照）

- **Phase 1**: 基盤構築（Docker、PostgreSQL、Redis、FastAPI、React）
- **Phase 2**: 認証システム（JWT、bcrypt、Redux）
- **Phase 3**: eBay OAuth連携（AES-256-GCM暗号化）
- **Phase 4**: データ同期（Trading API、Celery、**モックモード対応**）

### 🔄 Phase 5: トレンド分析（次のステップ）

**実装が必要なファイル:**

#### Backend
1. **`backend/app/models/trend_analysis.py`** - TrendAnalysisモデル
2. **`backend/app/services/trend_analysis_service.py`** - トレンド分析サービス
3. **`backend/app/tasks/trend_analysis.py`** - Celeryトレンド分析タスク
4. **`backend/app/api/trends.py`** - トレンドAPIエンドポイント
5. **`backend/app/schemas/trend.py`** - トレンドPydanticスキーマ
6. **Alembicマイグレーション** - trend_analysisテーブル

#### Frontend
1. **`frontend/src/components/trends/TrendChart.tsx`** - トレンドグラフ（Recharts使用）
2. **`frontend/src/components/trends/TrendList.tsx`** - トレンド商品リスト
3. **`frontend/src/pages/Trends.tsx`** - トレンドページ
4. **`frontend/src/services/trends.service.ts`** - トレンドAPIサービス
5. **`frontend/src/store/trendsSlice.ts`** - Reduxトレンドスライス

**実装内容:**

##### トレンドスコア計算ロジック
```python
def calculate_trend_score(listing_id: str, date: date) -> float:
    """
    トレンドスコア算出

    Score = (View成長率 × 0.4) + (Watch成長率 × 0.4) + (価格勢い × 0.2)
    """
    today_metrics = get_metrics(listing_id, date)
    yesterday_metrics = get_metrics(listing_id, date - timedelta(days=1))

    # 前日比成長率（ゼロ除算対策必要）
    view_growth = calculate_growth_rate(
        yesterday_metrics.view_count,
        today_metrics.view_count
    )
    watch_growth = calculate_growth_rate(
        yesterday_metrics.watch_count,
        today_metrics.watch_count
    )

    # 7日間移動平均
    week_avg = calculate_7day_average(listing_id, date)

    # スコア計算
    trend_score = (
        view_growth * 0.4 +
        watch_growth * 0.4 +
        calculate_price_momentum(listing_id, date) * 0.2
    )

    return trend_score
```

##### TOP10抽出
```python
def get_top_trending(account_id: str, date: date, limit: int = 10):
    """指定日のトレンドTOP10を取得"""
    trends = (db.query(TrendAnalysis)
              .join(Listing)
              .filter(
                  TrendAnalysis.analysis_date == date,
                  Listing.account_id == account_id,
                  TrendAnalysis.is_trending == True
              )
              .order_by(TrendAnalysis.trend_score.desc())
              .limit(limit)
              .all())
    return trends
```

##### Celeryタスク（app/celery_app.py に追加）
```python
'daily-trend-analysis': {
    'task': 'app.tasks.trend_analysis.analyze_all_trends',
    'schedule': crontab(hour=3, minute=0),  # 毎日午前3時（データ同期の後）
}
```

---

### 📅 Phase 6: ダッシュボード強化

**実装が必要な機能:**

#### Backend
1. **`backend/app/api/dashboard.py`** - ダッシュボードAPIエンドポイント
   - `GET /api/dashboard/summary` - KPIサマリー
   - `GET /api/dashboard/performance` - パフォーマンス推移

#### Frontend
1. **ダッシュボードのKPI表示を実データに接続**
   - 現在はハードコード（0件）→ APIから取得
2. **トレンドTOP10リスト表示**
   - `components/dashboard/TrendingItemsList.tsx`
3. **パフォーマンスグラフ**（Recharts使用）
   - View数・Watch数の推移グラフ
   - トレンドスコアの推移グラフ

**実装例:**
```typescript
// frontend/src/pages/Dashboard.tsx での修正
const Dashboard: React.FC = () => {
  const [stats, setStats] = useState(null);

  useEffect(() => {
    // APIから実際のデータを取得
    dashboardService.getSummary().then(setStats);
  }, []);

  return (
    // KPIカードに実データを表示
    <Typography variant="h3" color="primary">
      {stats?.active_listings || 0}
    </Typography>
  );
};
```

---

### 📅 Phase 7: 追加機能

**オプション実装:**

1. **通知機能**
   - トレンド商品検出時のメール通知
   - `backend/app/services/notification_service.py`

2. **Analytics API統合**
   - `backend/app/clients/analytics_api_client.py`
   - トラフィックレポートの取得

3. **Feed API統合**（バルクデータ取得）
   - `backend/app/clients/feed_api_client.py`
   - 初回同期の高速化

4. **レート制限機能**
   - `backend/app/utils/rate_limiter.py`
   - eBay API コール数管理

---

## ⚠️ 重要な実装上の注意

### 1. モックモードから本番モードへの移行

**現在の状態:**
- `EBAY_MOCK_MODE=true` でモックデータを使用中
- Trading APIクライアントは実装済みだが、実際のeBay APIは未テスト

**本番移行時のチェックリスト:**
1. ✅ eBay Developer Accountから Client ID/Secret を取得
2. ✅ `.env` に `EBAY_CLIENT_ID`, `EBAY_CLIENT_SECRET` を設定
3. ✅ `EBAY_MOCK_MODE=false` に変更
4. ✅ OAuth フローの動作確認
5. ✅ Trading API での実データ取得テスト
6. ✅ エラーハンドリングの確認（レート制限、トークン失効等）

### 2. eBay API制限への対応

**標準アカウントの制限:**
- **1日5,000コール**まで
- 2,000件の商品 × GetItem = 2,000コール/日
- GetMyeBaySelling（ページネーション）= 約10コール/日
- **合計: 約2,010コール/日**（制限内）

**制限を超える場合の対策:**
1. Redisキャッシング（同じ日に2回以上取得しない）
2. Feed APIでバルク取得（1タスクで全件取得）
3. eBayに申請して上限を拡大

### 3. データ整合性とエラー処理

**必須対応:**

#### ゼロ除算対策
```python
def calculate_growth_rate(old_value: int, new_value: int) -> float:
    """成長率計算（ゼロ除算対策）"""
    if old_value == 0:
        return 100.0 if new_value > 0 else 0.0
    return ((new_value - old_value) / old_value) * 100
```

#### 欠損データ対策
```python
# 前日のメトリクスがない場合
if not yesterday_metrics:
    # 初日のデータ or データ欠損
    # トレンドスコアは計算できないため、0を返すかスキップ
    return 0.0
```

#### トランザクション管理
```python
@celery.task
def sync_account_data(account_id):
    try:
        # データベーストランザクション
        with db.begin():
            # 同期処理
            service.sync_listings(account_id)
    except Exception as e:
        # ロールバック（自動）
        logger.error(f"Sync failed: {e}")
        raise
```

### 4. パフォーマンス最適化

**実装済み:**
- ✅ データベースインデックス（listings, daily_metrics）
- ✅ ユニーク制約（重複データ防止）
- ✅ Celeryバックグラウンドジョブ

**要対応:**
- ⏳ N+1問題の回避（join使用、eager loading）
- ⏳ ページネーション（リスティング一覧API）
- ⏳ Redisキャッシング（APIレスポンス）

**実装例:**
```python
# N+1問題の回避
listings = db.query(Listing).options(
    joinedload(Listing.daily_metrics)
).filter(Listing.account_id == account_id).all()
```

---

## 🔐 セキュリティチェックリスト

### 本番環境デプロイ前

- [ ] `.env`ファイルがgitignoreされている（✅完了）
- [ ] SECRET_KEY が強力なランダム文字列（32文字以上）
- [ ] ENCRYPTION_KEY が適切に生成されている（base64エンコード32バイト）
- [ ] データベースパスワードが強力
- [ ] CORS設定が本番ドメインのみ許可
- [ ] PostgreSQL Row Level Security (RLS) 有効化
- [ ] HTTPS使用（本番環境）
- [ ] eBay本番環境の認証情報使用

### コードレビュー項目

- [ ] SQLインジェクション対策（ORMパラメータバインド使用）
- [ ] XSS対策（フロントエンドでのエスケープ）
- [ ] CSRF対策（OAuth stateパラメータ検証済み）
- [ ] 認証トークンの適切な保存（localStorage使用中）
- [ ] パスワード平文保存なし（bcrypt使用中）
- [ ] OAuth トークン暗号化（AES-256-GCM使用中）

---

## 📊 データベーススキーマ（trend_analysis追加予定）

### trend_analysis テーブル（Phase 5で追加）

```sql
CREATE TABLE trend_analysis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    listing_id UUID NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    analysis_date DATE NOT NULL,

    -- 成長率
    view_growth_rate DECIMAL(8, 2),      -- View数成長率（%）
    watch_growth_rate DECIMAL(8, 2),     -- Watch数成長率（%）

    -- 移動平均
    view_7day_avg DECIMAL(10, 2),        -- View数7日間移動平均
    watch_7day_avg DECIMAL(10, 2),       -- Watch数7日間移動平均

    -- トレンドスコア
    trend_score DECIMAL(10, 2) NOT NULL, -- 総合スコア
    rank INTEGER,                        -- アカウント内順位
    is_trending BOOLEAN DEFAULT false,   -- TOP10フラグ

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(listing_id, analysis_date)
);

-- インデックス
CREATE INDEX idx_trend_analysis_date ON trend_analysis(analysis_date);
CREATE INDEX idx_trend_analysis_score ON trend_analysis(trend_score DESC);
CREATE INDEX idx_trend_analysis_trending ON trend_analysis(is_trending, analysis_date);
```

---

## 🐛 既知の問題と対処法

### 1. bcrypt警告メッセージ

**問題:**
```
(trapped) error reading bcrypt version
AttributeError: module 'bcrypt' has no attribute '__about__'
```

**対処:**
- 警告のみで動作に影響なし
- passlibがbcryptバージョンを読み取れないだけ
- 必要であれば `bcrypt==4.1.2` を維持

### 2. Docker Compose警告

**問題:**
```
the attribute `version` is obsolete
```

**対処:**
- Docker Compose v2の警告（動作に影響なし）
- 必要であれば `docker-compose.yml` から `version: '3.8'` を削除

---

## 🚀 開発再開時のクイックスタート

### 環境の起動

```bash
# すべてのサービスを起動
docker-compose up -d

# ログ確認
docker-compose logs -f backend

# データベースマイグレーション適用
docker-compose exec backend alembic upgrade head
```

### モックモードでのテスト

```bash
# .envファイルで確認
EBAY_MOCK_MODE=true

# テスト用ユーザーでログイン
# Email: test@example.com
# Password: Test1234

# 同期テスト（モックデータ生成）
curl -X POST http://localhost:8000/api/sync/trigger \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 次のタスク: Phase 5実装

1. TrendAnalysisモデル作成
2. トレンド分析サービス実装
3. Celeryタスク追加
4. APIエンドポイント作成
5. フロントエンドUI実装

---

## 📚 参考リソース

### eBay API
- [eBay Developer Program](https://developer.ebay.com/)
- [Trading API Reference](https://developer.ebay.com/Devzone/XML/docs/Reference/eBay/index.html)
- [OAuth 2.0 Guide](https://developer.ebay.com/api-docs/static/oauth-tokens.html)

### 技術ドキュメント
- [FastAPI](https://fastapi.tiangolo.com/)
- [Material-UI](https://mui.com/)
- [Recharts](https://recharts.org/)
- [Celery](https://docs.celeryq.dev/)
- [SQLAlchemy](https://www.sqlalchemy.org/)

### プロジェクト内ドキュメント
- `README.md` - セットアップとクイックスタート
- `.serena/memories/` - コードベース構造のドキュメント
  - `project_structure.md` - プロジェクト全体構造
  - `backend_models_overview.md` - バックエンドモデル詳細
  - `backend_services_overview.md` - サービス層詳細
  - `frontend_architecture.md` - フロントエンド構造
  - `api_contracts.md` - API仕様
  - `ebay_api_integration_guide.md` - eBay API統合ガイド
  - `development_workflow.md` - 開発ワークフロー

---

## 💡 開発のヒント

### Claude Codeでの効率的な開発

1. **段階的な実装**
   - Phase 5を小さなタスクに分解
   - 各タスクを完了後にテスト
   - 動作確認後にコミット

2. **モック活用**
   - eBay APIなしで開発継続可能
   - テストデータで動作確認
   - 本番API接続は最後

3. **エラーハンドリング**
   - ゼロ除算、NULL値、欠損データを考慮
   - ユーザーフレンドリーなエラーメッセージ
   - ログで詳細を記録

4. **コード品質**
   - 型ヒント必須（Python、TypeScript）
   - Docstring記述
   - 一貫したコーディングスタイル

---

**Happy Coding! 🚀**
