# eBay Trend Research Tool

eBay出品者向けのトレンドリサーチツール - 出品商品のパフォーマンスをモニタリングし、View数やWatch数が急成長しているトレンド商品を自動検出します。

## 🚀 主要機能

- **マルチアカウント対応**: 複数のeBayアカウントを一元管理
- **自動データ収集**: 1日1回、全出品物のメトリクスを自動取得（2,000件/アカウント）
- **トレンド分析**: View数・Watch数の成長率を分析し、TOP10を自動抽出
- **ダッシュボード**: トレンド商品の可視化とパフォーマンス推移表示
- **Analytics統合**: Click-Through Rate、Impression、Conversion Rateの詳細分析
- **Feed API統合**: 初回同期時の高速バルクデータ取得

## 🏗️ 技術スタック

| レイヤー | 技術 |
|---------|------|
| **Frontend** | React 18 + TypeScript + Material-UI + Recharts |
| **Backend** | FastAPI (Python 3.11+) |
| **Database** | PostgreSQL 16 |
| **Cache/Queue** | Redis 7 |
| **Background Jobs** | Celery + Celery Beat |
| **Container** | Docker + Docker Compose |

## 📋 前提条件

- Docker & Docker Compose
- eBay Developer Account ([登録はこちら](https://developer.ebay.com/))
- eBay App ID & Cert ID (Client ID & Client Secret)

## 🔧 セットアップ

### 1. リポジトリのクローン

```bash
git clone <repository-url>
cd my_trend_search
```

### 2. 環境変数の設定

`.env.example`をコピーして`.env`ファイルを作成し、必要な値を設定します。

```bash
cp .env.example .env
```

**重要な設定項目:**

```env
# Database
DATABASE_PASSWORD=your_secure_password

# Security (32文字以上の安全なランダム文字列を生成してください)
SECRET_KEY=your_secret_key_here
ENCRYPTION_KEY=your_base64_encoded_32byte_key_here

# eBay API (eBay Developer Portalから取得)
EBAY_CLIENT_ID=your_ebay_client_id
EBAY_CLIENT_SECRET=your_ebay_client_secret
EBAY_REDIRECT_URI=http://localhost:8000/api/ebay-accounts/callback
EBAY_ENVIRONMENT=sandbox  # または production

# モックモード（開発用）
EBAY_MOCK_MODE=true  # eBay認証情報なしで開発可能
```

**暗号化キーの生成方法:**

```python
# Python環境で実行
import os
import base64
key = base64.b64encode(os.urandom(32)).decode()
print(key)
```

### 3. Docker環境の起動

```bash
docker-compose up -d
```

初回起動時は、各イメージのビルドに数分かかります。

### 4. サービスの確認

すべてのサービスが正常に起動しているか確認します:

```bash
docker-compose ps
```

以下のサービスが稼働しているはずです:
- `ebay_trends_postgres` (PostgreSQL)
- `ebay_trends_redis` (Redis)
- `ebay_trends_backend` (FastAPI)
- `ebay_trends_celery_worker` (Celery Worker)
- `ebay_trends_celery_beat` (Celery Beat)
- `ebay_trends_frontend` (React)

### 5. アプリケーションへのアクセス

- **フロントエンド**: http://localhost:3000
- **バックエンドAPI**: http://localhost:8000
- **APIドキュメント**: http://localhost:8000/docs

## 📁 プロジェクト構造

```
my_trend_search/
├── backend/              # FastAPI バックエンド
│   ├── app/
│   │   ├── api/         # APIエンドポイント
│   │   ├── models/      # SQLAlchemyモデル
│   │   ├── services/    # ビジネスロジック
│   │   ├── clients/     # 外部APIクライアント (eBay Trading/Analytics/Feed)
│   │   ├── schemas/     # Pydanticスキーマ
│   │   ├── utils/       # ユーティリティ
│   │   └── tasks/       # Celeryタスク
│   ├── alembic/         # DBマイグレーション
│   └── tests/           # テスト
├── frontend/            # React フロントエンド
│   ├── public/
│   └── src/
│       ├── components/  # Reactコンポーネント
│       ├── pages/       # ページコンポーネント
│       ├── services/    # APIサービス
│       ├── store/       # Redux
│       └── theme/       # MUIテーマ
├── database/            # DB初期化スクリプト
├── docker-compose.yml   # Docker構成
├── .env.example         # 環境変数テンプレート
└── CLAUDE.md           # 開発ガイド
```

## 🔐 セキュリティ

- パスワード: bcryptでハッシュ化
- JWT認証: アクセストークン(24時間) + リフレッシュトークン(30日)
- eBay OAuth トークン: AES-256-GCMで暗号化して保存
- Row Level Security (RLS): テナントごとのデータ完全分離

## 📊 データベースマイグレーション

Alembicを使用してデータベーススキーマを管理します。

```bash
# マイグレーションの作成
docker-compose exec backend alembic revision --autogenerate -m "description"

# マイグレーションの適用
docker-compose exec backend alembic upgrade head

# マイグレーション履歴の確認
docker-compose exec backend alembic history
```

## 🧪 テスト

```bash
# バックエンドのテスト実行
docker-compose exec backend pytest

# カバレッジレポート付き
docker-compose exec backend pytest --cov=app --cov-report=html
```

## 📝 開発状況

### ✅ Phase 1-7: 完了

#### Phase 1: 基盤構築
- [x] プロジェクト骨格
- [x] Docker環境（PostgreSQL, Redis, FastAPI, React, Celery）
- [x] データベース設計
- [x] 基本的なFastAPIアプリケーション
- [x] Reactアプリケーション雛形

#### Phase 2: 認証システム
- [x] ユーザー登録・ログイン機能（Backend）
- [x] JWT発行・検証（アクセストークン24時間、リフレッシュトークン30日）
- [x] パスワードハッシュ化（bcrypt）
- [x] フロントエンドのログイン・登録画面
- [x] Redux状態管理
- [x] トークン自動リフレッシュ機能

#### Phase 3: eBay OAuth連携
- [x] OAuth 2.0フロー実装
- [x] トークン暗号化（AES-256-GCM）
- [x] トークン自動リフレッシュ
- [x] フロントエンドOAuth UI
- [x] アカウント接続・切断機能

#### Phase 4: データ同期
- [x] eBay Trading APIクライアント
- [x] Listing・DailyMetricモデル
- [x] データ同期サービス
- [x] Celeryバックグラウンドタスク（日次同期、トークンリフレッシュ）
- [x] 同期APIエンドポイント
- [x] **モックモード実装**（eBay認証情報なしで開発・テスト可能）

#### Phase 5: トレンド分析
- [x] TrendAnalysisモデル
- [x] トレンドスコア計算ロジック（View成長率×0.4 + Watch成長率×0.4 + 価格勢い×0.2）
- [x] TOP10抽出アルゴリズム
- [x] 7日間移動平均算出
- [x] トレンド分析Celeryタスク
- [x] トレンド分析APIエンドポイント

#### Phase 6: ダッシュボード強化
- [x] ダッシュボードKPI表示（実データ接続）
- [x] パフォーマンスグラフ（Recharts）
- [x] トレンドTOP10リスト表示
- [x] ダッシュボードAPI（Summary/Performance）
- [x] リアルタイムデータ更新

#### Phase 7: Analytics & Feed API統合
- [x] Analytics APIクライアント（CTR、Impression、Conversion）
- [x] Feed APIクライアント（バルク同期）
- [x] AnalyticsMetricモデル
- [x] Analytics同期サービス
- [x] Feed同期サービス
- [x] Analytics/Feed Celeryタスク

## 🧪 モックモードでの開発

eBayの認証情報が未取得の場合でも、モックモードで開発・テストが可能です。

**モックモードの有効化:**

`.env`ファイルで以下を設定:
```env
EBAY_MOCK_MODE=true
```

**モックモードの動作:**
- eBay APIの代わりに、リアルなモックデータを生成
- 50件の出品商品データを自動生成
- View数、Watch数、価格、Analytics指標（CTR、Impression等）を含む
- 実際のeBay API呼び出しは行わない

**本番モードへの切り替え:**

eBay認証情報取得後、以下を設定:
```env
EBAY_CLIENT_ID=your_actual_client_id
EBAY_CLIENT_SECRET=your_actual_client_secret
EBAY_MOCK_MODE=false
```

## 🔑 eBay API認証情報の取得

1. [eBay Developer Program](https://developer.ebay.com/)にアクセス
2. アカウント登録・ログイン
3. 「My Account」→「Application Keys」からアプリケーションを作成
4. **App ID (Client ID)** と **Cert ID (Client Secret)** を取得
5. OAuth Redirect URIを設定: `http://localhost:8000/api/ebay-accounts/callback`

## 📊 Celeryバックグラウンドタスク

以下のタスクが自動実行されます:

| タスク | スケジュール | 説明 |
|--------|-------------|------|
| **日次データ同期** | 毎日午前2:00（UTC） | Trading APIで全アカウントの出品物データを同期 |
| **Analytics同期** | 毎日午前2:30（UTC） | Analytics APIで詳細トラフィックデータを取得 |
| **トレンド分析** | 毎日午前3:00（UTC） | 成長率計算・TOP10抽出 |
| **トークンリフレッシュ** | 毎時 | 有効期限が2時間以内のトークンを更新 |

**手動同期の実行:**
```bash
# データ同期（Trading API）
curl -X POST http://localhost:8000/api/sync/trigger \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# トレンド分析
curl -X POST http://localhost:8000/api/trends/analyze \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# バルク同期（Feed API - 初回同期向け）
# 注: この機能は手動トリガーのみ（自動スケジュールなし）
```

## 🔄 データ取得フロー

### Trading API（日次更新）
- View数、Watch数を2,000件まで取得
- 毎日自動実行（午前2時UTC）

### Analytics API（日次更新）
- Click-Through Rate、Impression、Conversion Rate
- 50件ずつバッチ処理
- 毎日自動実行（午前2:30 UTC）

### Feed API（初回同期のみ）
- 2,000件以上の出品物を一度に取得
- Trading APIの10-100倍高速
- 手動トリガーのみ（自動スケジュールなし）

## 🐛 トラブルシューティング

### サービスが起動しない

```bash
# ログの確認
docker-compose logs backend
docker-compose logs frontend

# コンテナの再起動
docker-compose restart
```

### データベース接続エラー

```bash
# PostgreSQLの状態確認
docker-compose exec postgres pg_isready -U ebayuser

# データベースの再作成
docker-compose down -v
docker-compose up -d
```

### ポート競合エラー

既に使用中のポートがある場合は、`docker-compose.yml`でポート番号を変更してください。

## 📚 参考リンク

- [eBay Developer Program](https://developer.ebay.com/)
- [eBay Trading API Reference](https://developer.ebay.com/Devzone/XML/docs/Reference/eBay/index.html)
- [eBay Analytics API](https://developer.ebay.com/api-docs/sell/analytics/overview.html)
- [eBay Feed API](https://developer.ebay.com/api-docs/sell/feed/overview.html)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Material-UI](https://mui.com/)
- [Recharts](https://recharts.org/)
- [SQLAlchemy](https://www.sqlalchemy.org/)
- [Celery](https://docs.celeryq.dev/)

## 📄 ライセンス

MIT License

## 👥 開発者向け情報

詳細な開発ガイドは`CLAUDE.md`を参照してください。

---

**Happy Coding! 🚀**
