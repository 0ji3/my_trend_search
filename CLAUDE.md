# CLAUDE.md - eBay トレンドリサーチツール 開発ガイド

このドキュメントは、Claude Codeでの開発を円滑に進めるための包括的なガイドです。

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

## 🏗️ システムアーキテクチャ

### 技術スタック

| レイヤー | 技術 | バージョン |
|---------|------|-----------|
| **Frontend** | React + TypeScript + Material-UI | React 18.2+ |
| **Backend API** | FastAPI (Python) | Python 3.11+ |
| **Background Jobs** | Celery + APScheduler | - |
| **Database** | PostgreSQL | 18 |
| **Cache/Queue** | Redis | 7 |
| **Container** | Docker + Docker Compose | - |

### アーキテクチャ図

```
┌─────────────────────────────┐
│   Frontend (React + MUI)    │
│   Port: 3000                │
└─────────────┬───────────────┘
              │ HTTP/REST
              ▼
┌─────────────────────────────┐
│   FastAPI (CORS Enabled)    │
│   Port: 8000                │
└─────────────┬───────────────┘
              │
    ┌─────────┼─────────┐
    ▼         ▼         ▼
┌────────┐ ┌────────┐ ┌────────┐
│Auth    │ │Sync    │ │Trend   │
│Service │ │Service │ │Service │
└────────┘ └────────┘ └────────┘
              │
    ┌─────────┼─────────┐
    ▼         ▼         ▼
┌────────┐ ┌────────┐ ┌────────┐
│Postgres│ │Redis   │ │Celery  │
│18      │ │7       │ │Worker  │
└────────┘ └────────┘ └────────┘
```

---

## 📂 プロジェクト構造

```
ebay-trend-research/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI アプリケーション
│   │   ├── config.py               # 設定管理
│   │   ├── database.py             # DB接続
│   │   │
│   │   ├── models/                 # SQLAlchemy モデル
│   │   │   ├── __init__.py
│   │   │   ├── tenant.py
│   │   │   ├── oauth_credential.py
│   │   │   ├── ebay_account.py
│   │   │   ├── listing.py
│   │   │   ├── daily_metric.py
│   │   │   └── trend_analysis.py
│   │   │
│   │   ├── api/                    # APIエンドポイント
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── ebay_accounts.py
│   │   │   ├── listings.py
│   │   │   ├── trends.py
│   │   │   ├── dashboard.py
│   │   │   └── sync.py
│   │   │
│   │   ├── services/               # ビジネスロジック
│   │   │   ├── __init__.py
│   │   │   ├── auth_service.py
│   │   │   ├── ebay_oauth_service.py
│   │   │   ├── ebay_data_sync_service.py
│   │   │   ├── trend_analysis_service.py
│   │   │   └── notification_service.py
│   │   │
│   │   ├── clients/                # 外部API クライアント
│   │   │   ├── __init__.py
│   │   │   ├── ebay_client_base.py
│   │   │   ├── trading_api_client.py
│   │   │   ├── inventory_api_client.py
│   │   │   ├── analytics_api_client.py
│   │   │   └── feed_api_client.py
│   │   │
│   │   ├── schemas/                # Pydantic スキーマ
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── listing.py
│   │   │   └── trend.py
│   │   │
│   │   ├── utils/                  # ユーティリティ
│   │   │   ├── __init__.py
│   │   │   ├── security.py         # 暗号化・JWT
│   │   │   ├── logging.py
│   │   │   └── rate_limiter.py
│   │   │
│   │   ├── tasks/                  # Celery タスク
│   │   │   ├── __init__.py
│   │   │   ├── daily_sync.py
│   │   │   ├── trend_analysis.py
│   │   │   └── token_refresh.py
│   │   │
│   │   └── celery_app.py           # Celery設定
│   │
│   ├── alembic/                    # DBマイグレーション
│   │   ├── versions/
│   │   └── env.py
│   │
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_auth.py
│   │   └── test_trends.py
│   │
│   ├── Dockerfile
│   ├── requirements.txt
│   └── alembic.ini
│
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   │   ├── common/
│   │   │   │   ├── Header.tsx
│   │   │   │   ├── Sidebar.tsx
│   │   │   │   └── NotificationBell.tsx
│   │   │   ├── auth/
│   │   │   │   ├── LoginForm.tsx
│   │   │   │   └── RegisterForm.tsx
│   │   │   ├── dashboard/
│   │   │   │   ├── DashboardLayout.tsx
│   │   │   │   ├── KPICards.tsx
│   │   │   │   └── TrendingItemsList.tsx
│   │   │   ├── listings/
│   │   │   │   ├── ListingsTable.tsx
│   │   │   │   └── ListingDetail.tsx
│   │   │   └── trends/
│   │   │       ├── TrendChart.tsx
│   │   │       └── TrendList.tsx
│   │   │
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Listings.tsx
│   │   │   ├── Trends.tsx
│   │   │   └── Login.tsx
│   │   │
│   │   ├── services/
│   │   │   ├── api.ts
│   │   │   ├── auth.service.ts
│   │   │   └── listings.service.ts
│   │   │
│   │   ├── store/                  # Redux
│   │   │   ├── store.ts
│   │   │   ├── authSlice.ts
│   │   │   └── trendsSlice.ts
│   │   │
│   │   ├── theme/
│   │   │   └── theme.ts            # MUI テーマ
│   │   │
│   │   ├── types/
│   │   │   └── index.ts
│   │   │
│   │   ├── App.tsx
│   │   └── index.tsx
│   │
│   ├── Dockerfile
│   ├── package.json
│   └── tsconfig.json
│
├── database/
│   └── init.sql                    # 初期DDL
│
├── docker-compose.yml
├── .env.example
├── .gitignore
├── README.md
└── CLAUDE.md                       # このファイル
```

---

## 🗄️ データベース設計

### ER図

```
tenants (ユーザー)
  ↓ 1:N
oauth_credentials (OAuth認証情報)
  ↓ 1:N
ebay_accounts (eBayアカウント)
  ↓ 1:N
listings (出品商品)
  ↓ 1:N
daily_metrics (日次メトリクス)
  ↓ 1:N
trend_analysis (トレンド分析結果)
```

### 主要テーブル

#### tenants
```sql
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    business_name VARCHAR(255),
    timezone VARCHAR(50) DEFAULT 'UTC',
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
```

#### oauth_credentials
```sql
CREATE TABLE oauth_credentials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    access_token_encrypted BYTEA NOT NULL,
    access_token_iv BYTEA NOT NULL,
    access_token_auth_tag BYTEA NOT NULL,
    refresh_token_encrypted BYTEA NOT NULL,
    refresh_token_iv BYTEA NOT NULL,
    refresh_token_auth_tag BYTEA NOT NULL,
    access_token_expires_at TIMESTAMP NOT NULL,
    refresh_token_expires_at TIMESTAMP,
    scopes TEXT[] NOT NULL,
    is_valid BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tenant_id)
);
```

#### listings
```sql
CREATE TABLE listings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID NOT NULL REFERENCES ebay_accounts(id) ON DELETE CASCADE,
    item_id VARCHAR(50) NOT NULL,
    title TEXT NOT NULL,
    price DECIMAL(12, 2),
    currency VARCHAR(3) DEFAULT 'USD',
    category_id VARCHAR(50),
    category_name VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    image_url TEXT,
    item_specifics JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(account_id, item_id)
);
```

#### daily_metrics
```sql
CREATE TABLE daily_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    listing_id UUID NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    recorded_date DATE NOT NULL,
    view_count INTEGER DEFAULT 0,
    watch_count INTEGER DEFAULT 0,
    bid_count INTEGER DEFAULT 0,
    current_price DECIMAL(12, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(listing_id, recorded_date)
);
```

#### trend_analysis
```sql
CREATE TABLE trend_analysis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    listing_id UUID NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    analysis_date DATE NOT NULL,
    view_growth_rate DECIMAL(8, 2),
    watch_growth_rate DECIMAL(8, 2),
    view_7day_avg DECIMAL(10, 2),
    watch_7day_avg DECIMAL(10, 2),
    trend_score DECIMAL(10, 2) NOT NULL,
    rank INTEGER,
    is_trending BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(listing_id, analysis_date)
);
```

**完全なDDLは `database/init.sql` を参照**

---

## 🔌 API設計

### 認証エンドポイント

```
POST   /api/auth/register          ユーザー登録
POST   /api/auth/login             ログイン
POST   /api/auth/refresh           トークンリフレッシュ
POST   /api/auth/logout            ログアウト
```

### eBayアカウント管理

```
GET    /api/ebay-accounts                     アカウント一覧
GET    /api/ebay-accounts/auth-url            OAuth URL生成
POST   /api/ebay-accounts/callback            OAuth コールバック
DELETE /api/ebay-accounts/{account_id}        アカウント削除
```

### 出品商品

```
GET    /api/listings                          商品一覧
GET    /api/listings/{listing_id}             商品詳細
```

### トレンド分析

```
GET    /api/trends/top10                      本日のTOP10
GET    /api/trends/history/{listing_id}       商品別トレンド履歴
```

### ダッシュボード

```
GET    /api/dashboard/summary                 サマリー情報
GET    /api/dashboard/performance             パフォーマンス推移
```

### データ同期

```
POST   /api/sync/trigger                      手動同期トリガー
GET    /api/sync/status/{job_id}              同期ステータス確認
```

**詳細は各APIエンドポイントのコメントを参照**

---

## 🔐 セキュリティ設計

### 1. ユーザー認証
- **パスワードハッシュ化**: bcrypt (コスト係数12)
- **JWT**: アクセストークン(24時間) + リフレッシュトークン(30日間)
- **アルゴリズム**: HS256

### 2. eBay OAuth トークン暗号化
- **暗号化方式**: AES-256-GCM
- **キー管理**: 環境変数（将来的にはAWS KMS推奨）
- **保存形式**: 暗号化データ + IV + 認証タグ

```python
# 実装例
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

def encrypt_token(plaintext: str, master_key: bytes) -> dict:
    aesgcm = AESGCM(master_key)
    iv = os.urandom(12)
    ciphertext = aesgcm.encrypt(iv, plaintext.encode(), None)
    return {
        'encrypted': ciphertext[:-16],
        'iv': iv,
        'auth_tag': ciphertext[-16:]
    }
```

### 3. Row Level Security (RLS)
PostgreSQLのRLSを使用してテナントごとのデータを完全分離

```sql
ALTER TABLE listings ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_policy ON listings
    USING (account_id IN (
        SELECT id FROM ebay_accounts 
        WHERE tenant_id = current_setting('app.current_tenant_id')::uuid
    ));
```

### 4. API レート制限
- **FastAPI + slowapi**: 100リクエスト/分/ユーザー
- **eBay API**: キャッシング戦略でコール数削減

---

## 🎯 eBay API統合

### 使用するAPI

#### 1. Trading API (レガシーXML)
**用途**: 出品物の詳細情報、View/Watch数取得

```python
# GetMyeBaySelling - アクティブ出品物一覧
# GetItem - 個別商品詳細（View数、Watch数含む）

headers = {
    'X-EBAY-API-SITEID': '0',
    'X-EBAY-API-COMPATIBILITY-LEVEL': '1193',
    'X-EBAY-API-CALL-NAME': 'GetItem',
    'X-EBAY-API-IAF-TOKEN': oauth_token,
    'Content-Type': 'text/xml'
}
```

#### 2. Inventory API (RESTful)
**用途**: 在庫管理

```python
# GET /sell/inventory/v1/inventory_item
headers = {
    'Authorization': f'Bearer {access_token}',
    'Content-Type': 'application/json'
}
```

#### 3. Analytics API (RESTful)
**用途**: トラフィックレポート、クリック率等

```python
# GET /sell/analytics/v1/traffic_report
params = {
    'dimension': 'LISTING',
    'filter': f'startDate:[{start_date}],endDate:[{end_date}]',
    'metric': 'CLICK_THROUGH_RATE,LISTING_IMPRESSION_TOTAL'
}
```

#### 4. Feed API (RESTful)
**用途**: バルクデータ取得（初回同期、月次同期）

```python
# POST /sell/feed/v1/inventory_task
data = {
    'feedType': 'LMS_ACTIVE_INVENTORY_REPORT',
    'filterCriteria': {'listingStatus': ['ACTIVE']}
}
```

### OAuth 2.0 フロー

```python
# 1. 認証URL生成
auth_url = f"https://auth.ebay.com/oauth2/authorize?" \
           f"client_id={CLIENT_ID}&" \
           f"redirect_uri={REDIRECT_URI}&" \
           f"response_type=code&" \
           f"scope={SCOPES}"

# 2. 認証コード交換
response = requests.post(
    "https://api.ebay.com/identity/v1/oauth2/token",
    headers={'Authorization': f'Basic {base64_credentials}'},
    data={
        'grant_type': 'authorization_code',
        'code': authorization_code,
        'redirect_uri': REDIRECT_URI
    }
)

# 3. トークンリフレッシュ
response = requests.post(
    "https://api.ebay.com/identity/v1/oauth2/token",
    headers={'Authorization': f'Basic {base64_credentials}'},
    data={
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token,
        'scope': SCOPES  # 元のスコープと同じ
    }
)
```

### 必要なスコープ
```
https://api.ebay.com/oauth/api_scope/sell.inventory
https://api.ebay.com/oauth/api_scope/sell.inventory.readonly
https://api.ebay.com/oauth/api_scope/sell.fulfillment
https://api.ebay.com/oauth/api_scope/sell.analytics.readonly
```

**重要**: Trading API は特定のスコープ不要（任意のUser Access Tokenで使用可能）

---

## 🔄 バックグラウンドジョブ

### Celery Beat スケジュール

```python
# app/celery_app.py
from celery.schedules import crontab

beat_schedule = {
    'daily-data-sync': {
        'task': 'app.tasks.daily_sync.sync_all_accounts',
        'schedule': crontab(hour=2, minute=0),  # 毎日午前2時
    },
    'daily-trend-analysis': {
        'task': 'app.tasks.trend_analysis.analyze_all_trends',
        'schedule': crontab(hour=3, minute=0),  # 毎日午前3時
    },
    'token-refresh': {
        'task': 'app.tasks.token_refresh.refresh_expiring_tokens',
        'schedule': crontab(minute=0),  # 1時間ごと
    },
    'cleanup': {
        'task': 'app.tasks.cleanup.cleanup_old_data',
        'schedule': crontab(day_of_week=0, hour=1, minute=0),  # 毎週日曜午前1時
    },
}
```

### タスク例

```python
# app/tasks/daily_sync.py
from app.celery_app import celery

@celery.task(bind=True, max_retries=3)
def sync_account_data(self, account_id):
    try:
        service = eBayDataSyncService()
        result = service.sync_active_listings(account_id)
        return {'status': 'success', 'items': result.count}
    except Exception as e:
        self.retry(exc=e, countdown=60)
```

---

## 📊 トレンド分析ロジック

### スコア計算式

```python
def calculate_trend_score(listing_id: str, date: date) -> float:
    """
    トレンドスコア算出
    
    Score = (View成長率 × 0.4) + (Watch成長率 × 0.4) + (価格勢い × 0.2)
    """
    today_metrics = get_metrics(listing_id, date)
    yesterday_metrics = get_metrics(listing_id, date - timedelta(days=1))
    
    # 前日比成長率
    view_growth = ((today_metrics.view_count - yesterday_metrics.view_count) 
                   / yesterday_metrics.view_count * 100)
    watch_growth = ((today_metrics.watch_count - yesterday_metrics.watch_count) 
                    / yesterday_metrics.watch_count * 100)
    
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

### TOP10抽出

```python
def get_top_trending(account_id: str, date: date, limit: int = 10):
    """
    指定日のトレンドTOP10を取得
    """
    trends = (db.query(TrendAnalysis)
              .filter(TrendAnalysis.analysis_date == date)
              .filter(TrendAnalysis.account_id == account_id)
              .order_by(TrendAnalysis.trend_score.desc())
              .limit(limit)
              .all())
    
    return trends
```

---

## 🎨 フロントエンド実装ガイド

### Material-UI テーマ

```typescript
// src/theme/theme.ts
import { createTheme } from '@mui/material/styles';

export const theme = createTheme({
  palette: {
    primary: { main: '#1976d2' },
    secondary: { main: '#dc004e' },
    success: { main: '#2e7d32' },
  },
  typography: {
    fontFamily: 'Roboto, Arial, sans-serif',
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: { textTransform: 'none', borderRadius: 8 },
      },
    },
  },
});
```

### 主要コンポーネント例

#### ダッシュボード KPIカード

```typescript
import { Card, CardContent, Typography, Box } from '@mui/material';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';

export const KPICard = ({ title, value, change }) => (
  <Card>
    <CardContent>
      <Typography color="textSecondary" gutterBottom>
        {title}
      </Typography>
      <Typography variant="h4">{value}</Typography>
      <Box display="flex" alignItems="center" mt={1}>
        <TrendingUpIcon color="success" fontSize="small" />
        <Typography variant="body2" color="success.main" ml={0.5}>
          {change}%
        </Typography>
      </Box>
    </CardContent>
  </Card>
);
```

#### トレンドリスト

```typescript
import { List, ListItem, ListItemAvatar, Avatar, ListItemText, Chip } from '@mui/material';

export const TrendingList = ({ trends }) => (
  <List>
    {trends.map((trend, index) => (
      <ListItem key={trend.id}>
        <ListItemAvatar>
          <Avatar src={trend.image_url} />
        </ListItemAvatar>
        <ListItemText
          primary={trend.title}
          secondary={`$${trend.price}`}
        />
        <Chip 
          label={`+${trend.view_growth_rate}%`}
          color="success"
          size="small"
        />
      </ListItem>
    ))}
  </List>
);
```

### Redux Store

```typescript
// src/store/trendsSlice.ts
import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';

export const fetchTop10Trends = createAsyncThunk(
  'trends/fetchTop10',
  async (accountId: string) => {
    const response = await api.get(`/trends/top10?account_id=${accountId}`);
    return response.data;
  }
);

const trendsSlice = createSlice({
  name: 'trends',
  initialState: { top10: [], loading: false, error: null },
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(fetchTop10Trends.pending, (state) => {
        state.loading = true;
      })
      .addCase(fetchTop10Trends.fulfilled, (state, action) => {
        state.top10 = action.payload;
        state.loading = false;
      });
  },
});
```

---

## 🐳 Docker環境

### docker-compose.yml（簡略版）

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:18-alpine
    environment:
      POSTGRES_DB: ebay_trends
      POSTGRES_USER: ebayuser
      POSTGRES_PASSWORD: ${DATABASE_PASSWORD}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis
    environment:
      DATABASE_URL: postgresql://ebayuser:${DATABASE_PASSWORD}@postgres:5432/ebay_trends
      REDIS_URL: redis://redis:6379/0

  celery-worker:
    build: ./backend
    command: celery -A app.celery_app worker --loglevel=info
    depends_on:
      - postgres
      - redis

  celery-beat:
    build: ./backend
    command: celery -A app.celery_app beat --loglevel=info
    depends_on:
      - redis

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      REACT_APP_API_URL: http://localhost:8000/api
```

---

## 📦 依存パッケージ

### Backend (requirements.txt)

```
fastapi==0.109.0
uvicorn[standard]==0.27.0
sqlalchemy==2.0.25
alembic==1.13.1
psycopg2-binary==2.9.9
redis==5.0.1
celery==5.3.6
pydantic==2.5.3
pydantic-settings==2.1.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
slowapi==0.1.9
requests==2.31.0
lxml==5.1.0
cryptography==42.0.0
```

### Frontend (package.json)

```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.21.0",
    "@mui/material": "^5.15.0",
    "@mui/icons-material": "^5.15.0",
    "@emotion/react": "^11.11.0",
    "@emotion/styled": "^11.11.0",
    "@mui/x-data-grid": "^6.18.0",
    "@mui/x-date-pickers": "^6.18.0",
    "@reduxjs/toolkit": "^2.0.0",
    "react-redux": "^9.0.0",
    "axios": "^1.6.0",
    "recharts": "^2.10.0"
  }
}
```

---

## 🚀 開発の進め方（推奨順序）

### Phase 1: 基盤構築 (1-2週間)
1. ✅ プロジェクト骨格生成
2. ✅ Docker環境構築
3. ✅ データベースマイグレーション作成
4. ✅ 基本的なFastAPIアプリケーション
5. ✅ Reactアプリケーション雛形

### Phase 2: 認証システム (1週間)
1. ✅ ユーザー登録・ログイン機能
2. ✅ JWT発行・検証
3. ✅ フロントエンドのログイン画面

### Phase 3: eBay OAuth連携 (1-2週間)
1. ✅ OAuth 2.0フロー実装
2. ✅ トークン暗号化・保存
3. ✅ トークン自動リフレッシュ
4. ✅ フロントエンドのアカウント連携UI

### Phase 4: データ同期 (2週間)
1. ✅ Trading API クライアント実装
2. ✅ 出品物データ取得
3. ✅ daily_metrics テーブルへの保存
4. ✅ Celeryタスク実装
5. ✅ 手動同期トリガーAPI

### Phase 5: トレンド分析 (1-2週間)
1. ✅ トレンドスコア計算ロジック
2. ✅ TOP10抽出
3. ✅ trend_analysis テーブルへの保存
4. ✅ トレンド分析API

### Phase 6: ダッシュボード (2週間)
1. ✅ ダッシュボードレイアウト
2. ✅ KPIカード表示
3. ✅ トレンドTOP10リスト
4. ✅ パフォーマンスグラフ（Recharts）
5. ✅ 商品詳細モーダル

### Phase 7: 追加機能 (1-2週間)
1. ✅ 通知機能
2. ✅ Analytics API統合
3. ✅ Feed API統合（バルク取得）
4. ✅ レポート機能

### Phase 8: テスト・最適化 (1週間)
1. ✅ ユニットテスト
2. ✅ 統合テスト
3. ✅ パフォーマンスチューニング
4. ✅ バグ修正

---

## ⚠️ 重要な実装ポイント

### 1. セキュリティ
- ❗ **絶対にトークンを平文で保存しない**
- ❗ **環境変数で秘密情報を管理**
- ❗ **SQLインジェクション対策（ORMの適切な使用）**
- ❗ **CORS設定を適切に**

### 2. eBay API制限
- ❗ **1日5,000コールの制限**（標準アカウント）
- ❗ **キャッシング戦略必須**
- ❗ **リトライロジック実装**
- ❗ **レート制限エラーハンドリング**

### 3. データ整合性
- ❗ **トランザクション管理**
- ❗ **定期的な完全再同期**
- ❗ **エラー時のロールバック**

### 4. パフォーマンス
- ❗ **Redisキャッシング活用**
- ❗ **データベースインデックス最適化**
- ❗ **N+1問題の回避**
- ❗ **ページネーション実装**

---

## 🐛 トラブルシューティング

### eBay API関連

#### 問題: `invalid_grant` エラー
**原因**: リフレッシュトークンが無効化された
**解決策**: ユーザーに再度OAuth認証を実行してもらう

#### 問題: レート制限エラー
**原因**: API呼び出し上限超過
**解決策**: キャッシング、バッチ処理、Feed API活用

### データベース関連

#### 問題: 接続エラー
**原因**: PostgreSQL未起動 or 接続情報誤り
**解決策**: `docker-compose up postgres` 確認、DATABASE_URL検証

### Celery関連

#### 問題: タスクが実行されない
**原因**: Celery Worker未起動 or Redis接続失敗
**解決策**: `docker-compose logs celery-worker` でログ確認

---

## 📚 参考リソース

### eBay API ドキュメント
- [eBay Developer Program](https://developer.ebay.com/)
- [OAuth 2.0 Guide](https://developer.ebay.com/api-docs/static/oauth-tokens.html)
- [Trading API Reference](https://developer.ebay.com/Devzone/XML/docs/Reference/eBay/index.html)
- [Analytics API](https://developer.ebay.com/api-docs/sell/analytics/overview.html)

### 技術ドキュメント
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Material-UI](https://mui.com/)
- [SQLAlchemy](https://www.sqlalchemy.org/)
- [Celery](https://docs.celeryq.dev/)

---

## 💡 開発のヒント

### Claude Codeでの効率的な開発

1. **段階的な実装**
   - 小さな機能から始める
   - 動作確認しながら進める
   - コミットを細かく

2. **エラーハンドリング**
   - try-exceptを適切に配置
   - ログを詳細に出力
   - ユーザーフレンドリーなエラーメッセージ

3. **テスト**
   - 各機能の実装後にテスト作成
   - モックを活用（eBay APIなど）
   - エッジケースも考慮

4. **コード品質**
   - 型ヒント（Python）、TypeScript（Frontend）
   - docstringを書く
   - コメントは「なぜ」を説明

---

## 🎯 成功の指標

### 開発完了の定義
- ✅ ユーザーがeBayアカウントを連携できる
- ✅ 出品物データが自動収集される
- ✅ トレンドTOP10が正確に表示される
- ✅ ダッシュボードでパフォーマンスが可視化される
- ✅ 2,000件の商品を問題なく処理できる
- ✅ エラーハンドリングが適切

### パフォーマンス目標
- ダッシュボード表示: 2秒以内
- API応答時間: 1秒以内（95パーセンタイル）
- 2,000件の同期: 30分以内

---

## 📝 最後に

このプロジェクトは段階的に実装していくことが重要です。焦らず、各フェーズを確実に完成させてから次に進んでください。

質問や不明点があれば、このCLAUDE.mdを参照しながら開発を進めてください。

**Happy Coding! 🚀**