# eBay API Integration Guide

## Overview

The eBay Trend Research Tool uses multiple eBay APIs to collect listing data and metrics. This document provides implementation guidance for Phase 4 (Data Synchronization) and beyond.

## eBay API Credentials Setup

### 1. Get eBay Developer Account
1. Register at https://developer.ebay.com/
2. Create an Application (get App ID/Client ID and Cert ID/Secret)
3. Configure OAuth Redirect URI: `http://localhost:3000/oauth/callback`

### 2. Required Scopes (Already Implemented in Phase 3)
```python
REQUIRED_SCOPES = [
    "https://api.ebay.com/oauth/api_scope/sell.inventory",
    "https://api.ebay.com/oauth/api_scope/sell.inventory.readonly", 
    "https://api.ebay.com/oauth/api_scope/sell.fulfillment",
    "https://api.ebay.com/oauth/api_scope/sell.analytics.readonly",
]
```

### 3. Environment Configuration
```env
EBAY_CLIENT_ID=YourAppID
EBAY_CLIENT_SECRET=YourCertID
EBAY_REDIRECT_URI=http://localhost:3000/oauth/callback
EBAY_ENVIRONMENT=sandbox  # or 'production'
```

**API Base URLs**:
- Sandbox: `https://api.sandbox.ebay.com`
- Production: `https://api.ebay.com`
- Auth Sandbox: `https://auth.sandbox.ebay.com`
- Auth Production: `https://auth.ebay.com`

---

## API Architecture

### eBay API Types

eBay provides two types of APIs:

1. **RESTful APIs** (modern, recommended)
   - Inventory API
   - Analytics API
   - Feed API
   - Authentication: OAuth 2.0 User Access Token

2. **Trading API** (legacy XML-based)
   - GetMyeBaySelling
   - GetItem
   - GetSellerList
   - Authentication: OAuth 2.0 User Access Token (via X-EBAY-API-IAF-TOKEN header)

---

## Trading API (Primary for View/Watch Counts)

### Why Trading API?

**Critical**: View Count and Watch Count are **only available** in Trading API's GetItem call. RESTful APIs do NOT provide this data.

### Base Client Implementation

File: `backend/app/clients/trading_api_client.py`

```python
import requests
from typing import Dict, Any, Optional
from xml.etree import ElementTree as ET
from app.services.ebay_oauth_service import EbayOAuthService
from app.config import settings

class TradingAPIClient:
    """
    eBay Trading API Client (XML-based legacy API)
    Used for GetItem, GetMyeBaySelling to get View/Watch counts
    """
    
    def __init__(self, oauth_service: EbayOAuthService):
        self.oauth_service = oauth_service
        self.base_url = (
            "https://api.sandbox.ebay.com/ws/api.dll"
            if settings.EBAY_ENVIRONMENT == "sandbox"
            else "https://api.ebay.com/ws/api.dll"
        )
        self.site_id = "0"  # 0 = US, 3 = UK, 15 = Australia, etc.
        self.compatibility_level = "1193"
    
    def _get_headers(self, call_name: str, access_token: str) -> Dict[str, str]:
        """Generate headers for Trading API request"""
        return {
            'X-EBAY-API-SITEID': self.site_id,
            'X-EBAY-API-COMPATIBILITY-LEVEL': self.compatibility_level,
            'X-EBAY-API-CALL-NAME': call_name,
            'X-EBAY-API-IAF-TOKEN': access_token,  # OAuth token
            'Content-Type': 'text/xml; charset=utf-8',
        }
    
    def _build_request_xml(self, call_name: str, request_data: Dict[str, Any]) -> str:
        """Build XML request body"""
        xmlns = "urn:ebay:apis:eBLBaseComponents"
        root = ET.Element(f"{call_name}Request", xmlns=xmlns)
        
        # Add request data as XML elements
        for key, value in request_data.items():
            elem = ET.SubElement(root, key)
            elem.text = str(value)
        
        return ET.tostring(root, encoding='unicode')
    
    def get_item(self, item_id: str, access_token: str) -> Dict[str, Any]:
        """
        Get item details including View Count and Watch Count
        
        Returns:
            {
                'item_id': '123456789',
                'title': 'Item Title',
                'current_price': 29.99,
                'currency': 'USD',
                'view_count': 150,
                'watch_count': 12,
                'bid_count': 3,
                'quantity': 1,
                'quantity_sold': 0,
                'listing_type': 'FixedPriceItem',
                'listing_status': 'Active',
                'category_id': '12345',
                'category_name': 'Electronics',
                'image_url': 'https://...',
                'start_time': '2025-01-01T12:00:00Z',
                'end_time': '2025-01-31T12:00:00Z',
            }
        """
        headers = self._get_headers('GetItem', access_token)
        xml_body = self._build_request_xml('GetItem', {
            'ItemID': item_id,
            'DetailLevel': 'ReturnAll',
            'IncludeWatchCount': 'true',
        })
        
        response = requests.post(self.base_url, headers=headers, data=xml_body)
        response.raise_for_status()
        
        return self._parse_get_item_response(response.text)
    
    def _parse_get_item_response(self, xml_response: str) -> Dict[str, Any]:
        """Parse GetItem XML response"""
        root = ET.fromstring(xml_response)
        ns = {'ns': 'urn:ebay:apis:eBLBaseComponents'}
        
        item = root.find('.//ns:Item', ns)
        if item is None:
            raise ValueError("No Item element in response")
        
        def get_text(path: str, default: Any = None) -> Any:
            elem = item.find(path, ns)
            return elem.text if elem is not None else default
        
        return {
            'item_id': get_text('ns:ItemID'),
            'title': get_text('ns:Title'),
            'current_price': float(get_text('ns:SellingStatus/ns:CurrentPrice', 0)),
            'currency': get_text('ns:SellingStatus/ns:CurrentPrice[@currencyID]', 'USD'),
            'view_count': int(get_text('ns:HitCount', 0)),
            'watch_count': int(get_text('ns:WatchCount', 0)),
            'bid_count': int(get_text('ns:SellingStatus/ns:BidCount', 0)),
            'quantity': int(get_text('ns:Quantity', 0)),
            'quantity_sold': int(get_text('ns:SellingStatus/ns:QuantitySold', 0)),
            'listing_type': get_text('ns:ListingType'),
            'listing_status': get_text('ns:SellingStatus/ns:ListingStatus'),
            'category_id': get_text('ns:PrimaryCategory/ns:CategoryID'),
            'category_name': get_text('ns:PrimaryCategory/ns:CategoryName'),
            'image_url': get_text('ns:PictureDetails/ns:GalleryURL'),
            'start_time': get_text('ns:ListingDetails/ns:StartTime'),
            'end_time': get_text('ns:ListingDetails/ns:EndTime'),
        }
    
    def get_my_ebay_selling(self, access_token: str, page_number: int = 1, entries_per_page: int = 200) -> Dict[str, Any]:
        """
        Get list of active listings
        
        Returns:
            {
                'items': [{'item_id': '123', 'title': '...', ...}, ...],
                'total_pages': 10,
                'total_entries': 1500,
            }
        """
        headers = self._get_headers('GetMyeBaySelling', access_token)
        xml_body = f"""
        <GetMyeBaySellingRequest xmlns="urn:ebay:apis:eBLBaseComponents">
            <ActiveList>
                <Include>true</Include>
                <Pagination>
                    <EntriesPerPage>{entries_per_page}</EntriesPerPage>
                    <PageNumber>{page_number}</PageNumber>
                </Pagination>
            </ActiveList>
            <DetailLevel>ReturnAll</DetailLevel>
        </GetMyeBaySellingRequest>
        """
        
        response = requests.post(self.base_url, headers=headers, data=xml_body)
        response.raise_for_status()
        
        return self._parse_get_my_ebay_selling_response(response.text)
    
    def _parse_get_my_ebay_selling_response(self, xml_response: str) -> Dict[str, Any]:
        """Parse GetMyeBaySelling XML response"""
        root = ET.fromstring(xml_response)
        ns = {'ns': 'urn:ebay:apis:eBLBaseComponents'}
        
        items = []
        for item_elem in root.findall('.//ns:ActiveList/ns:ItemArray/ns:Item', ns):
            item_id = item_elem.find('ns:ItemID', ns)
            title = item_elem.find('ns:Title', ns)
            items.append({
                'item_id': item_id.text if item_id is not None else None,
                'title': title.text if title is not None else None,
            })
        
        pagination = root.find('.//ns:ActiveList/ns:PaginationResult', ns)
        total_pages = pagination.find('ns:TotalNumberOfPages', ns) if pagination else None
        total_entries = pagination.find('ns:TotalNumberOfEntries', ns) if pagination else None
        
        return {
            'items': items,
            'total_pages': int(total_pages.text) if total_pages is not None else 1,
            'total_entries': int(total_entries.text) if total_entries is not None else len(items),
        }
```

---

## RESTful APIs (Supplementary Data)

### Inventory API

**Use Case**: Get detailed inventory information, SKU mappings

File: `backend/app/clients/inventory_api_client.py`

```python
class InventoryAPIClient:
    """
    eBay Inventory API (RESTful)
    Used for inventory management, SKU data
    """
    
    def __init__(self):
        self.base_url = (
            "https://api.sandbox.ebay.com/sell/inventory/v1"
            if settings.EBAY_ENVIRONMENT == "sandbox"
            else "https://api.ebay.com/sell/inventory/v1"
        )
    
    def get_inventory_items(self, access_token: str, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
        """
        GET /sell/inventory/v1/inventory_item
        
        Returns inventory items with SKU, pricing, etc.
        Note: Does NOT include View/Watch counts
        """
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
        }
        params = {
            'limit': limit,
            'offset': offset,
        }
        
        response = requests.get(
            f"{self.base_url}/inventory_item",
            headers=headers,
            params=params
        )
        response.raise_for_status()
        return response.json()
```

### Analytics API

**Use Case**: Traffic reports, click-through rates (supplementary metrics)

File: `backend/app/clients/analytics_api_client.py`

```python
class AnalyticsAPIClient:
    """
    eBay Analytics API (RESTful)
    Used for traffic reports, performance metrics
    """
    
    def __init__(self):
        self.base_url = (
            "https://api.sandbox.ebay.com/sell/analytics/v1"
            if settings.EBAY_ENVIRONMENT == "sandbox"
            else "https://api.ebay.com/sell/analytics/v1"
        )
    
    def get_traffic_report(
        self,
        access_token: str,
        start_date: str,  # YYYY-MM-DD
        end_date: str,
        dimension: str = 'LISTING',
        metric: str = 'CLICK_THROUGH_RATE,LISTING_IMPRESSION_TOTAL'
    ) -> Dict[str, Any]:
        """
        GET /sell/analytics/v1/traffic_report
        
        Get traffic metrics (impressions, CTR, etc.)
        Note: Does NOT include View/Watch counts from listing page
        """
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
        }
        params = {
            'dimension': dimension,
            'filter': f'startDate:[{start_date}],endDate:[{end_date}]',
            'metric': metric,
        }
        
        response = requests.get(
            f"{self.base_url}/traffic_report",
            headers=headers,
            params=params
        )
        response.raise_for_status()
        return response.json()
```

### Feed API

**Use Case**: Bulk data download (initial sync, monthly full refresh)

File: `backend/app/clients/feed_api_client.py`

```python
class FeedAPIClient:
    """
    eBay Feed API (RESTful)
    Used for bulk inventory downloads (CSV/JSON)
    """
    
    def __init__(self):
        self.base_url = (
            "https://api.sandbox.ebay.com/sell/feed/v1"
            if settings.EBAY_ENVIRONMENT == "sandbox"
            else "https://api.ebay.com/sell/feed/v1"
        )
    
    def create_inventory_task(self, access_token: str) -> Dict[str, Any]:
        """
        POST /sell/feed/v1/inventory_task
        
        Request bulk inventory report generation
        Returns task_id to poll for completion
        """
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
        }
        data = {
            'feedType': 'LMS_ACTIVE_INVENTORY_REPORT',
            'filterCriteria': {
                'listingStatus': ['ACTIVE']
            }
        }
        
        response = requests.post(
            f"{self.base_url}/inventory_task",
            headers=headers,
            json=data
        )
        response.raise_for_status()
        return response.json()
    
    def get_task_status(self, access_token: str, task_id: str) -> Dict[str, Any]:
        """
        GET /sell/feed/v1/inventory_task/{task_id}
        
        Check if bulk report is ready
        """
        headers = {
            'Authorization': f'Bearer {access_token}',
        }
        
        response = requests.get(
            f"{self.base_url}/inventory_task/{task_id}",
            headers=headers
        )
        response.raise_for_status()
        return response.json()
    
    def download_result_file(self, access_token: str, task_id: str, save_path: str):
        """
        GET /sell/feed/v1/inventory_task/{task_id}/download
        
        Download generated report file
        """
        headers = {
            'Authorization': f'Bearer {access_token}',
        }
        
        response = requests.get(
            f"{self.base_url}/inventory_task/{task_id}/download",
            headers=headers,
            stream=True
        )
        response.raise_for_status()
        
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
```

---

## Data Synchronization Strategy

### Daily Sync Workflow

**Objective**: Collect View/Watch counts for all active listings daily

**Implementation** (Phase 4):

File: `backend/app/services/ebay_data_sync_service.py`

```python
from app.clients.trading_api_client import TradingAPIClient
from app.models import EbayAccount, Listing, DailyMetric
from datetime import date
from sqlalchemy.orm import Session

class EbayDataSyncService:
    """
    Handles daily synchronization of eBay listing data
    """
    
    def __init__(self, db: Session, oauth_service: EbayOAuthService):
        self.db = db
        self.oauth_service = oauth_service
        self.trading_client = TradingAPIClient(oauth_service)
    
    async def sync_account_listings(self, account: EbayAccount) -> Dict[str, Any]:
        """
        Sync all active listings for one eBay account
        
        Steps:
        1. Get valid access token
        2. Fetch all active item IDs (GetMyeBaySelling, paginated)
        3. For each item ID: GetItem to get View/Watch counts
        4. Update listings table (upsert)
        5. Insert daily_metrics record
        """
        # Get valid OAuth token
        access_token = await self.oauth_service.get_valid_access_token(
            self.db, 
            account.tenant_id
        )
        
        # Fetch all active item IDs
        all_items = []
        page = 1
        while True:
            result = self.trading_client.get_my_ebay_selling(
                access_token, 
                page_number=page, 
                entries_per_page=200
            )
            all_items.extend(result['items'])
            
            if page >= result['total_pages']:
                break
            page += 1
        
        # Sync each item
        synced_count = 0
        for item_summary in all_items:
            item_id = item_summary['item_id']
            
            # Get detailed item data including View/Watch
            item_data = self.trading_client.get_item(item_id, access_token)
            
            # Upsert listing
            listing = self._upsert_listing(account, item_data)
            
            # Insert daily metric
            self._insert_daily_metric(listing, item_data)
            
            synced_count += 1
        
        # Update last_sync_at
        account.last_sync_at = datetime.utcnow()
        self.db.commit()
        
        return {
            'account_id': str(account.id),
            'items_synced': synced_count,
            'sync_time': account.last_sync_at,
        }
    
    def _upsert_listing(self, account: EbayAccount, item_data: Dict[str, Any]) -> Listing:
        """Create or update listing record"""
        listing = self.db.query(Listing).filter(
            Listing.account_id == account.id,
            Listing.item_id == item_data['item_id']
        ).first()
        
        if not listing:
            listing = Listing(
                account_id=account.id,
                item_id=item_data['item_id'],
            )
            self.db.add(listing)
        
        # Update fields
        listing.title = item_data['title']
        listing.price = item_data['current_price']
        listing.currency = item_data['currency']
        listing.category_id = item_data['category_id']
        listing.category_name = item_data['category_name']
        listing.image_url = item_data['image_url']
        listing.is_active = (item_data['listing_status'] == 'Active')
        
        self.db.commit()
        return listing
    
    def _insert_daily_metric(self, listing: Listing, item_data: Dict[str, Any]):
        """Insert daily metric record"""
        today = date.today()
        
        # Check if metric already exists for today
        existing = self.db.query(DailyMetric).filter(
            DailyMetric.listing_id == listing.id,
            DailyMetric.recorded_date == today
        ).first()
        
        if existing:
            # Update existing (in case of re-sync)
            existing.view_count = item_data['view_count']
            existing.watch_count = item_data['watch_count']
            existing.bid_count = item_data['bid_count']
            existing.current_price = item_data['current_price']
        else:
            # Insert new
            metric = DailyMetric(
                listing_id=listing.id,
                recorded_date=today,
                view_count=item_data['view_count'],
                watch_count=item_data['watch_count'],
                bid_count=item_data['bid_count'],
                current_price=item_data['current_price'],
            )
            self.db.add(metric)
        
        self.db.commit()
```

### Celery Task

File: `backend/app/tasks/daily_sync.py`

```python
from app.celery_app import celery
from app.database import SessionLocal
from app.services.ebay_data_sync_service import EbayDataSyncService
from app.services.ebay_oauth_service import EbayOAuthService
from app.models import EbayAccount

@celery.task(bind=True, max_retries=3)
def sync_all_accounts(self):
    """
    Sync all active eBay accounts
    Scheduled to run daily at 2 AM
    """
    db = SessionLocal()
    try:
        oauth_service = EbayOAuthService()
        sync_service = EbayDataSyncService(db, oauth_service)
        
        # Get all active accounts
        accounts = db.query(EbayAccount).filter(
            EbayAccount.is_active == True
        ).all()
        
        results = []
        for account in accounts:
            try:
                result = sync_service.sync_account_listings(account)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to sync account {account.id}: {e}")
                # Continue with other accounts
        
        return {
            'status': 'success',
            'accounts_synced': len(results),
            'results': results,
        }
    except Exception as exc:
        self.retry(exc=exc, countdown=300)  # Retry after 5 minutes
    finally:
        db.close()
```

---

## Rate Limiting and Best Practices

### API Call Limits

**Standard eBay Account**:
- 5,000 calls per day
- Distributed across all API types

**Strategy to Stay Under Limit**:
1. **Use GetMyeBaySelling once** to get item IDs (~1 call per 200 items)
2. **Batch GetItem calls** (1 call per item, unavoidable for View/Watch)
3. **Cache results** in Redis for 23 hours
4. **Use Feed API** for initial bulk sync (1 task instead of thousands of calls)

### Example Calculation

- 2,000 active listings per account
- GetMyeBaySelling: 10 calls (200 items per page)
- GetItem: 2,000 calls (1 per item)
- **Total: 2,010 calls/day** (well under 5,000 limit)

### Rate Limiting Implementation

File: `backend/app/utils/rate_limiter.py`

```python
import redis
import time
from app.config import settings

class EbayRateLimiter:
    def __init__(self):
        self.redis_client = redis.from_url(settings.REDIS_URL)
        self.daily_limit = 5000
        self.key = "ebay_api_calls:daily"
    
    def check_and_increment(self) -> bool:
        """
        Check if we can make another API call
        Returns True if allowed, False if limit reached
        """
        current = self.redis_client.get(self.key)
        
        if current is None:
            # First call of the day
            self.redis_client.setex(self.key, 86400, 1)  # Expire in 24h
            return True
        
        current = int(current)
        if current >= self.daily_limit:
            return False
        
        self.redis_client.incr(self.key)
        return True
    
    def wait_if_needed(self):
        """Block until API call is allowed"""
        while not self.check_and_increment():
            time.sleep(60)  # Wait 1 minute
```

---

## Error Handling

### Common eBay API Errors

```python
class EbayAPIError(Exception):
    """Base eBay API error"""
    pass

class EbayAuthError(EbayAPIError):
    """OAuth token invalid or expired"""
    pass

class EbayRateLimitError(EbayAPIError):
    """API rate limit exceeded"""
    pass

class EbayItemNotFoundError(EbayAPIError):
    """Item no longer exists"""
    pass

def handle_ebay_api_error(response: requests.Response):
    """Parse eBay error response and raise appropriate exception"""
    if response.status_code == 401:
        raise EbayAuthError("Access token expired or invalid")
    elif response.status_code == 429:
        raise EbayRateLimitError("API rate limit exceeded")
    elif response.status_code == 404:
        raise EbayItemNotFoundError("Item not found")
    else:
        response.raise_for_status()
```

---

## Testing eBay API Integration

### Mock Trading API Response

File: `backend/tests/test_trading_api.py`

```python
import pytest
from app.clients.trading_api_client import TradingAPIClient

@pytest.fixture
def mock_get_item_response():
    return """
    <GetItemResponse xmlns="urn:ebay:apis:eBLBaseComponents">
        <Item>
            <ItemID>123456789</ItemID>
            <Title>Test Item</Title>
            <HitCount>150</HitCount>
            <WatchCount>12</WatchCount>
            <SellingStatus>
                <CurrentPrice currencyID="USD">29.99</CurrentPrice>
                <BidCount>0</BidCount>
            </SellingStatus>
        </Item>
    </GetItemResponse>
    """

def test_parse_get_item_response(mock_get_item_response):
    client = TradingAPIClient(oauth_service=None)
    result = client._parse_get_item_response(mock_get_item_response)
    
    assert result['item_id'] == '123456789'
    assert result['title'] == 'Test Item'
    assert result['view_count'] == 150
    assert result['watch_count'] == 12
    assert result['current_price'] == 29.99
```

---

## Summary

### Phase 4 Implementation Checklist

- [ ] Create `backend/app/clients/trading_api_client.py`
- [ ] Create `backend/app/clients/ebay_client_base.py` (shared utilities)
- [ ] Create `backend/app/services/ebay_data_sync_service.py`
- [ ] Create `backend/app/tasks/daily_sync.py` (Celery task)
- [ ] Create `backend/app/utils/rate_limiter.py`
- [ ] Add API endpoints: `POST /api/sync/trigger`, `GET /api/sync/status/{job_id}`
- [ ] Add Celery Beat schedule for 2 AM daily sync
- [ ] Add error handling for eBay API errors
- [ ] Add unit tests for API clients
- [ ] Test with eBay sandbox account

### Critical Notes

1. **View/Watch counts ONLY in Trading API** - must use GetItem
2. **Rate limit: 5,000 calls/day** - implement caching and monitoring
3. **Token refresh** - already implemented in Phase 3
4. **Pagination** - GetMyeBaySelling returns max 200 items per page
5. **Error handling** - gracefully handle deleted items, expired tokens
