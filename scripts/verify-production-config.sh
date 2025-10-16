#!/bin/bash

# ============================================================
# 本番環境設定の検証スクリプト
# ============================================================

echo "============================================================"
echo "本番環境設定の検証"
echo "============================================================"

# .env.productionファイルの存在確認
if [ ! -f ".env.production" ]; then
    echo "❌ エラー: .env.productionファイルが見つかりません"
    exit 1
fi

echo ""
echo "✅ .env.productionファイルが存在します"

# 必須項目のチェック
echo ""
echo "📋 必須項目のチェック:"

check_variable() {
    local var_name=$1
    local var_value=$(grep "^${var_name}=" .env.production | cut -d '=' -f 2-)

    if [ -z "$var_value" ]; then
        echo "   ❌ ${var_name}: 未設定"
        return 1
    elif [[ "$var_value" == *"YOUR_"* ]]; then
        echo "   ⚠️  ${var_name}: 設定が必要（プレースホルダー）"
        return 1
    else
        # 秘密情報はマスク
        if [[ "$var_name" == *"SECRET"* ]] || [[ "$var_name" == *"PASSWORD"* ]] || [[ "$var_name" == *"KEY"* ]]; then
            echo "   ✅ ${var_name}: ********** (設定済み)"
        else
            echo "   ✅ ${var_name}: ${var_value}"
        fi
        return 0
    fi
}

# 各項目をチェック
ERRORS=0

check_variable "DATABASE_PASSWORD" || ((ERRORS++))
check_variable "SECRET_KEY" || ((ERRORS++))
check_variable "ENCRYPTION_KEY" || ((ERRORS++))
check_variable "EBAY_CLIENT_ID" || ((ERRORS++))
check_variable "EBAY_CLIENT_SECRET" || ((ERRORS++))
check_variable "EBAY_REDIRECT_URI" || ((ERRORS++))
check_variable "EBAY_ENVIRONMENT" || ((ERRORS++))
check_variable "DEBUG" || ((ERRORS++))

# eBay環境の確認
echo ""
echo "🔍 eBay環境の確認:"
EBAY_ENV=$(grep "^EBAY_ENVIRONMENT=" .env.production | cut -d '=' -f 2)
if [ "$EBAY_ENV" == "production" ]; then
    echo "   ✅ EBAY_ENVIRONMENT=production"
else
    echo "   ⚠️  EBAY_ENVIRONMENT=${EBAY_ENV} (本番環境ではproductionを推奨)"
fi

# DEBUG設定の確認
echo ""
echo "🔍 DEBUG設定の確認:"
DEBUG_VALUE=$(grep "^DEBUG=" .env.production | cut -d '=' -f 2)
if [ "$DEBUG_VALUE" == "False" ]; then
    echo "   ✅ DEBUG=False (本番環境に適切)"
else
    echo "   ⚠️  DEBUG=${DEBUG_VALUE} (本番環境ではFalseを推奨)"
fi

# セキュリティキーの強度チェック
echo ""
echo "🔐 セキュリティキーの確認:"
SECRET_KEY=$(grep "^SECRET_KEY=" .env.production | cut -d '=' -f 2)
SECRET_KEY_LEN=${#SECRET_KEY}
if [ $SECRET_KEY_LEN -ge 32 ]; then
    echo "   ✅ SECRET_KEY: 十分な長さ (${SECRET_KEY_LEN}文字)"
else
    echo "   ⚠️  SECRET_KEY: 短すぎます (${SECRET_KEY_LEN}文字、32文字以上推奨)"
    ((ERRORS++))
fi

# CORS設定の確認
echo ""
echo "🌐 CORS設定の確認:"
CORS_ORIGINS=$(grep "^CORS_ORIGINS=" .env.production | cut -d '=' -f 2)
echo "   📋 CORS_ORIGINS: ${CORS_ORIGINS}"
if [[ "$CORS_ORIGINS" == *"localhost"* ]]; then
    echo "   ⚠️  本番環境でlocalhostが含まれています"
fi

# 結果表示
echo ""
echo "============================================================"
if [ $ERRORS -eq 0 ]; then
    echo "✅ すべての設定が正常です！"
    echo "============================================================"
    echo ""
    echo "次のステップ:"
    echo "  1. eBay認証情報を設定 (まだの場合)"
    echo "  2. ./scripts/switch-to-production.sh を実行"
    echo "  3. ngrokを起動: ngrok http 8000"
    echo "  4. OAuth接続をテスト"
else
    echo "⚠️  ${ERRORS}個の問題が見つかりました"
    echo "============================================================"
    echo ""
    echo "修正が必要な項目:"
    echo "  - .env.productionファイルを編集してください"
    echo "  - YOUR_で始まる値を実際の値に置き換えてください"
fi
echo ""
