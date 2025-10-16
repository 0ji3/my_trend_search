# 本番環境セットアップガイド

このドキュメントでは、ローカルDockerで本番環境を構築する手順を説明します。

---

## 📋 前提条件

- Docker & Docker Compose がインストールされていること
- eBay Developer Portalで**本番アプリケーション**を作成済みであること
- ngrok がインストールされていること（HTTPS接続用）

---

## 🚀 本番環境構築手順

### Step 1: eBay本番アプリケーションの作成

1. **eBay Developer Portal**にアクセス
   - https://developer.ebay.com/my/keys

2. **本番用アプリケーションを作成**
   - Application Type: Production
   - Grant Type: Authorization Code Grant

3. **認証情報を取得**
   - App ID (Client ID)
   - Cert ID (Client Secret)
   - RuName (Redirect URI Name)を作成

4. **RuNameの設定**
   - ngrokを起動: `ngrok http 8000`
   - Redirect URL: `https://your-ngrok-url.ngrok-free.app/api/ebay-accounts/callback`
   - Privacy Policy URL: 任意のURL

---

### Step 2: 環境変数の設定

1. **.env.productionファイルを編集**
   ```bash
   nano .env.production
   ```

2. **eBay本番用認証情報を設定**
   ```bash
   # eBay API Configuration (本番用)
   EBAY_CLIENT_ID=your_production_client_id
   EBAY_CLIENT_SECRET=your_production_client_secret
   EBAY_REDIRECT_URI=your_production_runame
   EBAY_ENVIRONMENT=production
   ```

3. **CORS設定を更新（オプション）**
   ```bash
   # 本番ドメインがある場合
   CORS_ORIGINS=https://yourdomain.com,http://localhost:3000
   ```

---

### Step 3: 本番環境への切り替え

**自動スクリプトを使用（推奨）:**
```bash
./scripts/switch-to-production.sh
```

**または手動で実行:**
```bash
# .envファイルを本番用に切り替え
cp .env.production .env

# Dockerコンテナを再起動
docker-compose down
docker-compose up -d

# データベースマイグレーション
docker-compose exec backend alembic upgrade head
```

---

### Step 4: ngrokの起動

本番環境でもngrokを使用してHTTPSアクセスを提供します:

```bash
ngrok http 8000
```

**表示されたHTTPS URLをコピー:**
```
Forwarding   https://xxxx-xxxx.ngrok-free.app -> http://localhost:8000
```

**eBay Developer PortalでRuNameのRedirect URLを更新:**
```
https://xxxx-xxxx.ngrok-free.app/api/ebay-accounts/callback
```

---

### Step 5: OAuth接続テスト

1. **フロントエンドにアクセス**
   ```
   http://localhost:3000
   ```

2. **ダッシュボードでOAuth接続**
   - "Connect eBay Account"ボタンをクリック
   - **本番のeBayアカウント**でログイン
   - 認証完了後、ダッシュボードに戻る

3. **接続確認**
   ```bash
   docker-compose exec backend python -c "
   from app.database import SessionLocal
   from app.models.ebay_account import EbayAccount
   db = SessionLocal()
   accounts = db.query(EbayAccount).all()
   for acc in accounts:
       print(f'✅ {acc.username} - {acc.ebay_user_id}')
   db.close()
   "
   ```

---

## 🔍 本番環境の動作確認

### ヘルスチェック
```bash
curl http://localhost:8000/health
```

### ログ確認
```bash
# バックエンドログ
docker-compose logs -f backend

# Celeryワーカーログ
docker-compose logs -f celery_worker

# Celery Beatログ
docker-compose logs -f celery_beat
```

### データベース確認
```bash
docker-compose exec backend python -c "
from app.database import SessionLocal
from app.models.tenant import Tenant
db = SessionLocal()
tenants = db.query(Tenant).all()
print(f'Tenants: {len(tenants)}')
db.close()
"
```

---

## 🔄 開発環境への戻し方

```bash
./scripts/switch-to-development.sh
```

または

```bash
# バックアップから復元
cp .env.backup.YYYYMMDD_HHMMSS .env

# Dockerコンテナを再起動
docker-compose restart
```

---

## 🔐 セキュリティチェックリスト

本番環境運用前に以下を確認してください:

### 環境変数
- [ ] `SECRET_KEY`が強力なランダム文字列（32文字以上）
- [ ] `ENCRYPTION_KEY`が適切に生成されている（base64エンコード32バイト）
- [ ] `POSTGRES_PASSWORD`が強力
- [ ] `DEBUG=False`に設定
- [ ] `LOG_LEVEL=WARNING`または`ERROR`に設定

### CORS設定
- [ ] `CORS_ORIGINS`に本番ドメインのみ許可
- [ ] ローカルホスト（`localhost:3000`）を削除（本番ドメインがある場合）

### eBay設定
- [ ] `EBAY_ENVIRONMENT=production`
- [ ] `EBAY_CLIENT_ID`が本番用
- [ ] `EBAY_CLIENT_SECRET`が本番用
- [ ] `EBAY_REDIRECT_URI`が本番用RuName

### データベース
- [ ] PostgreSQLのパスワードが強力
- [ ] データベースバックアップの設定
- [ ] Row Level Security (RLS) 検討

### ngrok（開発環境）
- [ ] ngrokのHTTPS URLが最新
- [ ] eBay RuNameのRedirect URLが最新のngrok URLに更新

**ngrokの詳細設定：**

1. **ngrokをインストール** (Windows):
   - https://ngrok.com/download からダウンロード
   - アカウント登録してauthtokenを取得
   - `ngrok authtoken YOUR_TOKEN`で認証

2. **ngrokを起動**:
   ```bash
   ngrok http 8000
   ```

3. **eBay Developer PortalでRuNameを設定**:
   - Redirect URL: `https://your-ngrok-url.ngrok-free.app/api/ebay-accounts/callback`
   - RuNameをコピーして`EBAY_REDIRECT_URI`に設定（識別子のみ、完全なURLではない）

4. **Dockerを再起動**:
   ```bash
   docker-compose restart backend
   ```

**注意:** ngrokのURLは再起動のたびに変わるため、変更されたらeBay RuNameのRedirect URLも更新してください。

---

## 📊 本番環境の監視

### メトリクス確認
```bash
curl http://localhost:8000/api/metrics/statistics
```

### 同期状態確認
```bash
curl http://localhost:8000/api/sync/status \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### エラーログ確認
```bash
curl http://localhost:8000/api/metrics/errors \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 🆘 トラブルシューティング

### OAuth接続が失敗する
- ngrok URLが変更されていないか確認
- eBay RuNameのRedirect URLが正しいか確認
- eBay認証情報が本番用か確認

### データベース接続エラー
```bash
# データベースログ確認
docker-compose logs postgres

# コンテナ再起動
docker-compose restart postgres backend
```

### Celeryタスクが実行されない
```bash
# Celery Beat確認
docker-compose logs celery_beat

# Celeryワーカー確認
docker-compose logs celery_worker

# Redis接続確認
docker-compose exec redis redis-cli ping
```

---

## 📝 本番環境と開発環境の違い

| 項目 | 開発環境 | 本番環境 |
|------|---------|---------|
| eBay環境 | Sandbox | Production |
| DEBUG | True | False |
| LOG_LEVEL | INFO | WARNING |
| API Docs | 有効 | 無効 |
| CORS | localhost許可 | 本番ドメインのみ |
| セキュリティキー | 開発用 | 本番用（強力） |

---

## 🚀 次のステップ

1. **実際のeBayデータで動作確認**
   - 本番eBayアカウントで出品物を作成
   - データ同期をテスト
   - トレンド分析を確認

2. **本番ドメインの取得（オプション）**
   - ドメインを取得
   - SSL証明書を設定
   - ngrokから実際のHTTPSに移行

3. **本番データベースの構築（オプション）**
   - PostgreSQLを専用サーバーに移行
   - データベースバックアップの自動化
   - Row Level Securityの設定

4. **監視・アラート設定**
   - Slack/Email通知の実装
   - メトリクスダッシュボードの構築
   - エラーログの集約

---

**Happy Production! 🎉**
