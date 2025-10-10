# eBay Trend Research Tool

eBay出品者向けのトレンドリサーチツール - 出品商品のパフォーマンスをモニタリングし、View数やWatch数が急成長しているトレンド商品を自動検出します。

## 🚀 主要機能

- **マルチアカウント対応**: 複数のeBayアカウントを一元管理
- **自動データ収集**: 1日1回、全出品物のメトリクスを自動取得（2,000件/アカウント）
- **トレンド分析**: View数・Watch数の成長率を分析し、TOP10を自動抽出
- **ダッシュボード**: トレンド商品の可視化とパフォーマンス推移表示
- **通知機能**: トレンド商品検出時のアラート

## 🏗️ 技術スタック

| レイヤー | 技術 |
|---------|------|
| **Frontend** | React 18 + TypeScript + Material-UI |
| **Backend** | FastAPI (Python 3.11+) |
| **Database** | PostgreSQL 16 |
| **Cache/Queue** | Redis 7 |
| **Background Jobs** | Celery + APScheduler |
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
│   │   ├── clients/     # 外部APIクライアント
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

### ✅ Phase 1: 基盤構築（完了）
- [x] プロジェクト骨格
- [x] Docker環境
- [x] データベース設計
- [x] 基本的なFastAPIアプリケーション
- [x] Reactアプリケーション雛形

### 🔄 Phase 2: 認証システム（次のステップ）
- [ ] ユーザー登録・ログイン機能
- [ ] JWT発行・検証
- [ ] フロントエンドのログイン画面

### 📅 今後の予定
- Phase 3: eBay OAuth連携
- Phase 4: データ同期
- Phase 5: トレンド分析
- Phase 6: ダッシュボード
- Phase 7: 追加機能
- Phase 8: テスト・最適化

詳細は`CLAUDE.md`を参照してください。

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
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Material-UI](https://mui.com/)
- [SQLAlchemy](https://www.sqlalchemy.org/)
- [Celery](https://docs.celeryq.dev/)

## 📄 ライセンス

MIT License

## 👥 開発者向け情報

詳細な開発ガイドは`CLAUDE.md`を参照してください。

---

**Happy Coding! 🚀**
