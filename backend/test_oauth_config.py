"""
Test eBay OAuth configuration
"""
import sys
sys.path.insert(0, '/app')

from app.services.ebay_oauth_service import EbayOAuthService
from app.config import settings

def test_oauth_config():
    print("=" * 60)
    print("eBay OAuth Configuration Test")
    print("=" * 60)

    # Display configuration
    print(f"\n📋 Current Configuration:")
    print(f"   Client ID: {settings.EBAY_CLIENT_ID[:30]}...")
    print(f"   Client Secret: {settings.EBAY_CLIENT_SECRET[:20]}...")
    print(f"   Redirect URI: {settings.EBAY_REDIRECT_URI}")
    print(f"   Environment: {settings.EBAY_ENVIRONMENT}")
    print(f"   Mock Mode: {settings.EBAY_MOCK_MODE}")

    # Initialize service
    oauth_service = EbayOAuthService()

    print(f"\n🔗 OAuth Endpoints:")
    print(f"   Auth URL: {oauth_service.auth_url}")
    print(f"   Token URL: {oauth_service.token_url}")

    # Generate authorization URL
    print(f"\n🔑 Generating Authorization URL...")
    try:
        auth_url, state = oauth_service.generate_authorization_url()
        print(f"   ✅ Success!")
        print(f"   State: {state[:20]}...")
        print(f"\n📎 Authorization URL:")
        print(f"   {auth_url[:100]}...")
        print(f"\n   Full URL length: {len(auth_url)} characters")

        # Check required scopes
        print(f"\n📜 Required Scopes:")
        for scope in oauth_service.REQUIRED_SCOPES:
            print(f"   - {scope}")

        print(f"\n✅ OAuth configuration is valid!")
        print(f"\n💡 Next Steps:")
        print(f"   1. Start frontend: http://localhost:3000")
        print(f"   2. Register/Login to your account")
        print(f"   3. Connect eBay account from dashboard")
        print(f"   4. Complete OAuth flow")

    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_oauth_config()
