# eBay API Call Limits - Complete Reference

このドキュメントは、eBay API Call Limitsの公式情報をまとめたものです。

**公式ドキュメント**: https://developer.ebay.com/develop/get-started/api-call-limits

---

## 📊 プロジェクトで使用しているAPIのリミット

このプロジェクトで使用している主要APIのデフォルトリミット（標準アカウント）:

| API | 1日のコール数上限 | 使用目的 |
|-----|------------------|---------|
| **Trading API** | **5,000 calls/day** | GetMyeBaySelling, GetItem (Watch数取得) |
| **Analytics API** | **リソース依存** | Traffic Report (View数、CTR、Conversion取得) |
| **Feed API** | **100,000 calls/day** | 初回バルク同期（大量データ一括取得） |

### 現在の使用状況

**1日あたりの推定コール数**:
- Trading API: **約4,329コール/日**
  - GetMyeBaySelling: 2アカウント × 9ページ = 18コール
  - GetItem: 4,311アイテム = 4,311コール
  - **使用率: 86.6%** (4,329 / 5,000)

- Analytics API: **約40コール/日** (推定)
  - Traffic Report: 4,311アイテム ÷ 50件/バッチ ≈ 87バッチ
  - ※ただし、リソース別の詳細リミットは公式ドキュメントに未記載

- Feed API: **手動トリガーのみ**
  - 初回同期時のみ使用（通常は未使用）

---

## 🔢 eBay API Call Limits 完全リスト

### 1. Sell APIs（出品者向けAPI）

| API | デフォルトリミット |
|-----|-------------------|
| Account API | 25,000 calls/day |
| Feed API | 100,000 calls/day |
| Inventory API | 2,000,000 calls/day |
| Logistics API | 2,500,000 calls/day |
| Marketing Promotion API | 100,000 calls/day |
| **Analytics API** | **リソース依存** ※詳細は個別確認必要 |

### 2. Buy APIs（購入者向けAPI）※追加ライセンス必要

| API | デフォルトリミット |
|-----|-------------------|
| Browse API | 5,000 calls/day |
| Deal API | 5,000 calls/day |
| Feed Beta API | 10,000 - 75,000 calls/day (リソース依存) |

### 3. Commerce APIs

| API | デフォルトリミット |
|-----|-------------------|
| Media API (image/document) | 1,000,000 calls/day |
| Catalog API | 10,000 calls/day |
| Notification API | 10,000 calls/day |

### 4. Traditional APIs（レガシーAPI）

| API | デフォルトリミット |
|-----|-------------------|
| **Trading API** | **5,000 calls/day** |
| Merchandising API | 5,000 calls/day |

---

## ⚡ レート制限（Rate Limiting）

### Commerce Media API
- **POST操作**: 50リクエスト / 5秒（ユーザーレベル）
- 画像アップロード時に適用

### その他のAPI
- 公式ドキュメントには具体的なレート制限の記載なし
- 一般的には**秒単位・分単位のレート制限**が存在する可能性あり
- 過剰なリクエストは`429 Too Many Requests`エラーを返す

---

## 📈 API使用量の確認方法

eBay APIレスポンスヘッダーに使用状況が含まれる場合があります：

```http
X-EBAY-API-CALL-LIMIT: 5000
X-EBAY-API-CALLS-REMAINING: 671
X-EBAY-API-TIME-UNTIL-RESET: 43200
```

**注意**: すべてのAPIがこれらのヘッダーを返すわけではありません。

---

## 🚀 APIリミットの引き上げ方法

### 条件
1. **Application Growth Check**を完了する
2. eBayの**API License Agreement**を遵守していることを確認
3. 効率的なAPI使用を実証

### 手順
1. eBay Developer Portalにログイン
2. Application Growth Checkを申請
3. eBayによる審査（使用状況、遵守状況を確認）
4. 承認後、上限が引き上げられる

### 引き上げ例
- Trading API: 5,000 → 10,000+ calls/day
- Analytics API: 標準 → プレミアム tier
- Feed API: 100,000 → 無制限（要審査）

---

## ⚠️ 重要な注意事項

### 1. リミットのリセットタイミング
- **毎日午前0時 UTC**にリセット
- タイムゾーンに注意（JST = UTC+9）

### 2. 複数アカウント使用時
- **アプリケーション単位**でリミットがカウントされる
- 2アカウント分の同期でも、1つのアプリケーションのリミットを共有

### 3. OAuth Tokenのレート制限
- OAuth token取得・リフレッシュにも**別途レート制限**あり
- 詳細は別ドキュメント参照: https://developer.ebay.com/api-docs/static/oauth-tokens.html

### 4. エラーハンドリング
- `429 Too Many Requests` → レート制限超過、待機が必要
- `403 Forbidden` → 日次リミット超過、翌日まで待機

---

## 📊 プロジェクトの推奨事項

### 現在の状況（2アカウント、4,311アイテム）
- ✅ **Trading API**: 4,329コール（86.6%使用）→ **リミット内**
- ✅ **Analytics API**: 推定40-90コール → **リミット内**（詳細確認必要）
- ✅ **Feed API**: 初回のみ使用 → **リミット内**

### 将来のスケーラビリティ
| アイテム数 | Trading API使用率 | 対策 |
|-----------|------------------|------|
| 5,000件 | 100% | **Feed API併用**または**リミット引き上げ申請** |
| 10,000件 | 200%（超過） | **必須: リミット引き上げ** |
| 20,000件 | 400%（大幅超過） | **必須: プレミアムTier** |

### 最適化戦略

#### 短期（現状維持）
1. ✅ Redisキャッシング（同じデータを再取得しない）
2. ✅ バッチ処理（Analytics APIは50件ずつ）
3. ✅ 重複同期防止（daily_metricsのUnique制約）

#### 中期（6,000-10,000アイテム対応）
1. ⬜ **Feed API活用**（初回同期を高速化）
2. ⬜ **差分同期**（変更があったアイテムのみ取得）
3. ⬜ **API Call Limit引き上げ申請**

#### 長期（10,000+アイテム対応）
1. ⬜ **プレミアムTierへ移行**
2. ⬜ **マルチアプリケーション戦略**（複数のApp IDで分散）
3. ⬜ **eBay Partnerプログラム参加**

---

## 🔗 関連リソース

- [API Call Limits公式ドキュメント](https://developer.ebay.com/develop/get-started/api-call-limits)
- [OAuth Token Rate Limits](https://developer.ebay.com/api-docs/static/oauth-tokens.html)
- [Trading API Reference](https://developer.ebay.com/Devzone/XML/docs/Reference/eBay/index.html)
- [Analytics API Reference](https://developer.ebay.com/api-docs/sell/analytics/overview.html)
- [Feed API Reference](https://developer.ebay.com/api-docs/sell/feed/overview.html)
- [Application Growth Check申請](https://developer.ebay.com/my/application-growth)

---

**Last Updated**: 2025-10-17
**Status**: Trading API使用率86.6%、リミット内で正常動作中
