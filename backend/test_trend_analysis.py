"""
Test script for Trend Analysis

既存のモックデータを使用してトレンド分析をテストします。
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from datetime import date, timedelta
from app.database import SessionLocal
from app.models.ebay_account import EbayAccount
from app.services.trend_analysis_service import TrendAnalysisService


def test_trend_analysis():
    """トレンド分析のテスト"""
    print("=" * 80)
    print("Trend Analysis Test")
    print("=" * 80)

    db = SessionLocal()

    try:
        # 既存のeBayアカウントを取得
        account = db.query(EbayAccount).filter(
            EbayAccount.is_active == True
        ).first()

        if not account:
            print("❌ No connected eBay account found. Please run data sync first.")
            return

        print(f"\n✅ Found eBay account: {account.username or account.ebay_user_id}")
        print(f"   Account ID: {account.id}")

        # トレンド分析サービスを初期化
        service = TrendAnalysisService(db)

        # 今日の日付
        today = date.today()

        print(f"\n📊 Starting trend analysis for date: {today}")
        print("-" * 80)

        # アカウント全体の分析を実行
        results = service.analyze_account(str(account.id), today)

        print(f"\n✅ Trend analysis completed!")
        print(f"   Analyzed listings: {len(results)}")

        if results:
            print(f"\n📈 Trend Analysis Results (Top 10):")
            print("-" * 80)

            # TOP 10を取得
            top_trends = service.get_top_trending(str(account.id), today, limit=10)

            for i, trend in enumerate(top_trends, 1):
                listing = trend.listing
                print(f"\n{i}. {listing.title[:60]}...")
                print(f"   Item ID: {listing.item_id}")
                print(f"   Trend Score: {trend.trend_score}")
                print(f"   View Growth: {trend.view_growth_rate}%")
                print(f"   Watch Growth: {trend.watch_growth_rate}%")
                print(f"   7-day Avg Views: {trend.view_7day_avg}")
                print(f"   7-day Avg Watches: {trend.watch_7day_avg}")
                print(f"   Rank: #{trend.rank}")

            # 統計情報
            print("\n" + "=" * 80)
            print("📊 Statistics:")
            print("-" * 80)

            total_score = sum(t.trend_score for t in results)
            avg_score = total_score / len(results) if results else 0

            print(f"Total analyzed: {len(results)} listings")
            print(f"Top trending: {len(top_trends)} listings")
            print(f"Average trend score: {avg_score:.2f}")
            print(f"Max trend score: {max((t.trend_score for t in results), default=0):.2f}")
            print(f"Min trend score: {min((t.trend_score for t in results), default=0):.2f}")

        else:
            print("⚠️  No trend analysis results. Make sure you have daily metrics data.")
            print("    Run data sync first to populate daily_metrics table.")

    except Exception as e:
        print(f"\n❌ Error during trend analysis: {e}")
        import traceback
        traceback.print_exc()

    finally:
        db.close()

    print("\n" + "=" * 80)
    print("Test completed!")
    print("=" * 80)


if __name__ == "__main__":
    test_trend_analysis()
