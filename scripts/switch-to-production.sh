#!/bin/bash

# ============================================================
# 本番環境への切り替えスクリプト
# ============================================================

set -e  # エラーが発生したら停止

echo "============================================================"
echo "本番環境への切り替え"
echo "============================================================"

# 現在のディレクトリを確認
if [ ! -f ".env.production" ]; then
    echo "❌ エラー: .env.productionファイルが見つかりません"
    echo "   プロジェクトのルートディレクトリで実行してください"
    exit 1
fi

# バックアップを作成
echo ""
echo "📦 現在の.envファイルをバックアップ中..."
if [ -f ".env" ]; then
    cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
    echo "   ✅ バックアップ完了: .env.backup.$(date +%Y%m%d_%H%M%S)"
fi

# 本番環境設定をコピー
echo ""
echo "🔄 本番環境設定を適用中..."
cp .env.production .env
echo "   ✅ .env.production → .env にコピー完了"

# eBay認証情報の確認
echo ""
echo "⚠️  eBay本番用認証情報の確認"
echo "   以下の値が設定されているか確認してください:"
grep "EBAY_CLIENT_ID" .env
grep "EBAY_CLIENT_SECRET" .env | sed 's/=.*/=***HIDDEN***/'
grep "EBAY_REDIRECT_URI" .env
grep "EBAY_ENVIRONMENT" .env

if grep -q "YOUR_PRODUCTION" .env; then
    echo ""
    echo "❌ 警告: eBay本番用認証情報が設定されていません"
    echo "   .envファイルを編集して、以下を設定してください:"
    echo "   - EBAY_CLIENT_ID"
    echo "   - EBAY_CLIENT_SECRET"
    echo "   - EBAY_REDIRECT_URI"
    echo ""
    read -p "このまま続行しますか？ (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "中断しました"
        exit 1
    fi
fi

# Dockerコンテナを停止
echo ""
echo "🛑 Dockerコンテナを停止中..."
docker-compose down
echo "   ✅ コンテナ停止完了"

# Dockerコンテナを起動
echo ""
echo "🚀 本番環境でDockerコンテナを起動中..."
docker-compose up -d
echo "   ✅ コンテナ起動完了"

# コンテナが起動するまで待機
echo ""
echo "⏳ コンテナの起動を待機中..."
sleep 5

# データベースマイグレーション
echo ""
echo "🔧 データベースマイグレーションを実行中..."
docker-compose exec -T backend alembic upgrade head
echo "   ✅ マイグレーション完了"

# ヘルスチェック
echo ""
echo "🏥 ヘルスチェック中..."
sleep 2
if curl -s http://localhost:8000/health > /dev/null; then
    echo "   ✅ バックエンド正常稼働"
else
    echo "   ❌ バックエンドに接続できません"
fi

echo ""
echo "============================================================"
echo "✅ 本番環境への切り替え完了！"
echo "============================================================"
echo ""
echo "📝 次のステップ:"
echo "   1. eBay Developer Portalで本番アプリケーションを作成"
echo "   2. .envファイルに本番用認証情報を設定"
echo "   3. ngrokを起動: ngrok http 8000"
echo "   4. eBay RuNameのRedirect URLを設定"
echo "   5. ダッシュボードでOAuth接続: http://localhost:3000"
echo ""
echo "🔍 ログ確認:"
echo "   docker-compose logs -f backend"
echo ""
