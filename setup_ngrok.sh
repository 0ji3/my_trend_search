#!/bin/bash
# ngrok setup for eBay OAuth HTTPS callback

echo "================================================"
echo "ngrok Setup for eBay OAuth HTTPS"
echo "================================================"

# Check if ngrok is installed
if ! command -v ngrok &> /dev/null; then
    echo "❌ ngrok is not installed"
    echo ""
    echo "Please install ngrok:"
    echo "1. Visit: https://ngrok.com/download"
    echo "2. Download and install for your OS"
    echo "3. Sign up for free account: https://dashboard.ngrok.com/signup"
    echo "4. Get your authtoken: https://dashboard.ngrok.com/get-started/your-authtoken"
    echo "5. Run: ngrok config add-authtoken YOUR_TOKEN"
    exit 1
fi

echo "✅ ngrok is installed"
echo ""
echo "Starting ngrok tunnel to port 8000..."
echo ""
echo "================================================"
echo "IMPORTANT: After ngrok starts, you will see:"
echo "  Forwarding: https://xxxx-xxxx-xxxx.ngrok-free.app -> http://localhost:8000"
echo ""
echo "Use the HTTPS URL (https://xxxx-xxxx-xxxx.ngrok-free.app) for:"
echo "1. eBay RuName Redirect URL: https://xxxx-xxxx-xxxx.ngrok-free.app/api/ebay-accounts/callback"
echo "2. Update EBAY_REDIRECT_URI in .env to the RuName with this URL"
echo "================================================"
echo ""
echo "Press Ctrl+C to stop ngrok"
echo ""

# Start ngrok
ngrok http 8000
