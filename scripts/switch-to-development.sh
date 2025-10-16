#!/bin/bash

# ============================================================
# 開発環境への切り替えスクリプト
# ============================================================

set -e  # エラーが発生したら停止

echo "============================================================"
echo "開発環境への切り替え"
echo "============================================================"

# バックアップから復元
echo ""
echo "🔄 開発環境設定を復元中..."

# 最新のバックアップを探す
LATEST_BACKUP=$(ls -t .env.backup.* 2>/dev/null | head -1)

if [ -n "$LATEST_BACKUP" ]; then
    echo "   📦 バックアップが見つかりました: $LATEST_BACKUP"
    cp "$LATEST_BACKUP" .env
    echo "   ✅ 開発環境設定を復元完了"
else
    echo "   ⚠️  バックアップが見つかりません"
    echo "   デフォルトの開発環境設定を使用します"

    # Sandbox環境に設定
    sed -i 's/EBAY_ENVIRONMENT=production/EBAY_ENVIRONMENT=sandbox/g' .env 2>/dev/null || true
    sed -i 's/DEBUG=False/DEBUG=True/g' .env 2>/dev/null || true
    sed -i 's/LOG_LEVEL=WARNING/LOG_LEVEL=INFO/g' .env 2>/dev/null || true
fi

# 環境確認
echo ""
echo "📋 現在の設定:"
grep "EBAY_ENVIRONMENT" .env
grep "DEBUG" .env
grep "LOG_LEVEL" .env

# Dockerコンテナを再起動
echo ""
echo "🔄 Dockerコンテナを再起動中..."
docker-compose down
docker-compose up -d
echo "   ✅ コンテナ再起動完了"

# コンテナが起動するまで待機
echo ""
echo "⏳ コンテナの起動を待機中..."
sleep 5

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
echo "✅ 開発環境への切り替え完了！"
echo "============================================================"
echo ""
echo "📝 開発環境情報:"
echo "   - バックエンド: http://localhost:8000"
echo "   - フロントエンド: http://localhost:3000"
echo "   - API Docs: http://localhost:8000/docs"
echo ""
