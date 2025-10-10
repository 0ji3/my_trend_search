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
5. **Analytics統合**: CTR、Impression、Conversion Rateの詳細分析
6. **Feed API**: 初回同期時の高速バルクデータ取得

---

## 📝 実装状況

### ✅ Phase 1-7: 完了

すべての主要機能が実装され、モックモードで動作確認可能な状態です。

#### Phase 1: 基盤構築
- Docker環境（PostgreSQL 16, Redis 7, FastAPI, React 18, Celery）
- データベース設計とマイグレーション
- プロジェクト構造の構築

#### Phase 2: 認証システム
- ユーザー登録・ログイン（JWT、bcrypt）
- トークン自動リフレッシュ
- Redux状態管理

#### Phase 3: eBay OAuth連携
- OAuth 2.0フロー実装
- トークン暗号化（AES-256-GCM）
- アカウント接続・切断機能

#### Phase 4: データ同期
- Trading API統合（View/Watch数取得）
- Listing・DailyMetricモデル
- Celeryバックグラウンドタスク
- **モックモード実装**

#### Phase 5: トレンド分析
- TrendAnalysisモデル
- トレンドスコア計算（View成長率×0.4 + Watch成長率×0.4 + 価格勢い×0.2）
- TOP10自動抽出
- 7日間移動平均算出

#### Phase 6: ダッシュボード強化
- KPIダッシュボード（実データ接続）
- パフォーマンスグラフ（Recharts）
- トレンドTOP10リスト表示

#### Phase 7: Analytics & Feed API統合
- Analytics API（CTR、Impression、Conversion Rate）
- Feed API（バルク同期、初回同期高速化）
- AnalyticsMetricモデル

---

## 🔄 自動バッチスケジュール

Celery Beatによる自動実行スケジュール:

```
02:00 UTC → Trading API データ同期（View/Watch数）
02:30 UTC → Analytics API 同期（CTR/Impression/Conversion）
03:00 UTC → トレンド分析（成長率計算、TOP10抽出）
毎時      → OAuth トークンリフレッシュ
```

**手動トリガー可能なタスク:**
- Feed API バルク同期（初回同期向け）
- 特定アカウントのみの同期・分析

---

## 📊 データベーススキーマ

### 主要テーブル

#### tenants
- テナント情報（マルチテナント対応）

#### oauth_credentials
- OAuth トークン（AES-256-GCM暗号化）

#### ebay_accounts
- eBayアカウント情報

#### listings
- 出品物情報（item_id, title, price, category等）

#### daily_metrics
- 日次メトリクス（View数、Watch数、価格）
- Unique constraint: (listing_id, recorded_date)

#### trend_analysis
- トレンド分析結果
- トレンドスコア、成長率、ランキング
- Unique constraint: (listing_id, analysis_date)

#### analytics_metrics
- Analytics APIメトリクス（CTR、Impression、Conversion Rate）
- Unique constraint: (listing_id, recorded_date)

---

## ⚠️ 重要な実装上の注意

### 1. モックモードから本番モードへの移行

**現在の状態:**
- `EBAY_MOCK_MODE=true` でモックデータを使用可能
- すべてのeBay APIクライアントがモックモード対応

**本番移行時のチェックリスト:**
1. eBay Developer Accountから Client ID/Secret を取得
2. `.env` に `EBAY_CLIENT_ID`, `EBAY_CLIENT_SECRET` を設定
3. `EBAY_MOCK_MODE=false` に変更
4. OAuth フローの動作確認
5. Trading/Analytics/Feed API での実データ取得テスト
6. エラーハンドリングの確認（レート制限、トークン失効等）

### 2. eBay API制限への対応

**標準アカウントの制限:**
- **1日5,000コール**まで

**使用状況:**
- Trading API: 約2,010コール/日（2,000件の商品 + ページネーション）
- Analytics API: 約40コール/日（50件ずつバッチ処理）
- **合計: 約2,050コール/日**（制限内）

**制限を超える場合の対策:**
1. Redisキャッシング（同じ日に2回以上取得しない）
2. Feed APIでバルク取得（1タスクで全件取得、初回のみ）
3. eBayに申請して上限を拡大

### 3. データ整合性とエラー処理

**実装済みの対策:**

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
    # トレンドスコアは0を返す
    return 0.0
```

#### トランザクション管理
```python
@celery.task
def sync_account_data(account_id):
    try:
        with db.begin():
            service.sync_listings(account_id)
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        raise  # リトライ機構が動作
```

### 4. パフォーマンス最適化

**実装済み:**
- ✅ データベースインデックス（全主要テーブル）
- ✅ ユニーク制約（重複データ防止）
- ✅ Celeryバックグラウンドジョブ
- ✅ バッチ処理（Analytics: 50件ずつ）

**推奨事項:**
- N+1問題の回避（joinedload使用）
- ページネーション（大量データ取得時）
- Redisキャッシング（APIレスポンス）

**実装例:**
```python
# N+1問題の回避
listings = db.query(Listing).options(
    joinedload(Listing.daily_metrics),
    joinedload(Listing.trend_analyses)
).filter(Listing.account_id == account_id).all()
```

---

## 🔐 セキュリティチェックリスト

### 本番環境デプロイ前

- [x] `.env`ファイルがgitignoreされている
- [ ] SECRET_KEY が強力なランダム文字列（32文字以上）
- [ ] ENCRYPTION_KEY が適切に生成されている（base64エンコード32バイト）
- [ ] データベースパスワードが強力
- [ ] CORS設定が本番ドメインのみ許可
- [ ] PostgreSQL Row Level Security (RLS) 有効化
- [ ] HTTPS使用（本番環境）
- [ ] eBay本番環境の認証情報使用

### コードレビュー項目

- [x] SQLインジェクション対策（ORMパラメータバインド使用）
- [x] XSS対策（フロントエンドでのエスケープ）
- [x] CSRF対策（OAuth stateパラメータ検証済み）
- [x] 認証トークンの適切な保存（localStorage使用中）
- [x] パスワード平文保存なし（bcrypt使用中）
- [x] OAuth トークン暗号化（AES-256-GCM使用中）

---

## 🔄 データ取得フロー

### Trading API（日次更新）
**用途**: 基本的なView/Watch数の取得
- スケジュール: 毎日午前2:00 UTC
- 取得データ: View数、Watch数、価格、在庫数
- 制限: 2,000件/アカウント

### Analytics API（日次更新）
**用途**: 詳細トラフィック分析
- スケジュール: 毎日午前2:30 UTC
- 取得データ: Click-Through Rate、Impression、Conversion Rate
- バッチ処理: 50件ずつ

### Feed API（初回同期のみ）
**用途**: 初回の大量データ一括取得
- スケジュール: 手動トリガーのみ
- 取得データ: 全出品物情報（2,000件以上対応）
- 利点: Trading APIの10-100倍高速

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

### 2. Docker Compose警告

**問題:**
```
the attribute `version` is obsolete
```

**対処:**
- Docker Compose v2の警告（動作に影響なし）

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

# フロントエンド: http://localhost:3000
# ユーザー登録後、ダッシュボードにアクセス

# データ同期テスト（モックデータ生成）
curl -X POST http://localhost:8000/api/sync/trigger \
  -H "Authorization: Bearer YOUR_TOKEN"

# トレンド分析テスト
curl -X POST http://localhost:8000/api/trends/analyze \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 本番API接続テスト

```bash
# .envを本番モードに設定
EBAY_MOCK_MODE=false
EBAY_CLIENT_ID=your_actual_client_id
EBAY_CLIENT_SECRET=your_actual_client_secret

# コンテナ再起動
docker-compose restart backend celery_worker celery_beat

# OAuth接続テスト
# http://localhost:3000 でダッシュボードにアクセスし、eBayアカウント連携
```

---

## 📚 参考リソース

### eBay API
- [eBay Developer Program](https://developer.ebay.com/)
- [Trading API Reference](https://developer.ebay.com/Devzone/XML/docs/Reference/eBay/index.html)
- [Analytics API](https://developer.ebay.com/api-docs/sell/analytics/overview.html)
- [Feed API](https://developer.ebay.com/api-docs/sell/feed/overview.html)
- [OAuth 2.0 Guide](https://developer.ebay.com/api-docs/static/oauth-tokens.html)

### 技術ドキュメント
- [FastAPI](https://fastapi.tiangolo.com/)
- [Material-UI](https://mui.com/)
- [Recharts](https://recharts.org/)
- [Celery](https://docs.celeryq.dev/)
- [SQLAlchemy](https://www.sqlalchemy.org/)
- [Alembic](https://alembic.sqlalchemy.org/)
- [Redux Toolkit](https://redux-toolkit.js.org/)

### プロジェクト内ドキュメント
- `README.md` - セットアップとクイックスタート
- `.serena/memories/` - コードベース構造のドキュメント

---

## 💡 開発のヒント

### Claude Codeでの効率的な開発

1. **段階的な実装**
   - 機能を小さなタスクに分解
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

## 🎯 今後の拡張案（オプション）

### 1. 通知機能
- トレンド商品検出時のメール/Slack通知
- カスタムアラート設定

### 2. レポート機能
- 週次・月次レポート自動生成
- PDF/Excelエクスポート

### 3. 競合分析
- 競合商品のトラッキング
- 価格比較機能

### 4. AI推奨機能
- 最適な出品タイミング提案
- 価格最適化アドバイス

---

**Happy Coding! 🚀**

**プロジェクト完成おめでとうございます！** 🎉

全Phase完了により、eBay出品者向けの包括的なトレンドリサーチツールが完成しました。
モックモードで開発・テストが可能で、実際のeBay APIへの切り替えも簡単に行えます。
