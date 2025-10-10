"""
eBay Trading API Client
Legacy XML-based API used to get View Count and Watch Count
"""
import random
from typing import Dict, Any, List
from xml.etree import ElementTree as ET
from datetime import datetime, timedelta
from app.clients.ebay_client_base import EbayClientBase, handle_ebay_api_error


class TradingAPIClient(EbayClientBase):
    """
    eBay Trading API Client (XML-based legacy API)
    Used for GetItem, GetMyeBaySelling to get View/Watch counts

    Supports mock mode when eBay credentials are not available
    """

    def __init__(self):
        super().__init__()
        self.base_url = self._get_base_url('trading')
        self.site_id = "0"  # 0 = US, 3 = UK, 15 = Australia
        self.compatibility_level = "1193"

    def _get_headers(self, call_name: str, access_token: str) -> Dict[str, str]:
        """Generate headers for Trading API request"""
        return {
            'X-EBAY-API-SITEID': self.site_id,
            'X-EBAY-API-COMPATIBILITY-LEVEL': self.compatibility_level,
            'X-EBAY-API-CALL-NAME': call_name,
            'X-EBAY-API-IAF-TOKEN': access_token,
            'Content-Type': 'text/xml; charset=utf-8',
        }

    def _build_request_xml(self, call_name: str, request_data: Dict[str, Any]) -> str:
        """Build XML request body"""
        xmlns = "urn:ebay:apis:eBLBaseComponents"
        root = ET.Element(f"{call_name}Request", xmlns=xmlns)

        for key, value in request_data.items():
            if isinstance(value, dict):
                # Nested elements
                parent = ET.SubElement(root, key)
                for sub_key, sub_value in value.items():
                    sub_elem = ET.SubElement(parent, sub_key)
                    sub_elem.text = str(sub_value)
            else:
                elem = ET.SubElement(root, key)
                elem.text = str(value)

        return ET.tostring(root, encoding='unicode')

    def get_item(self, item_id: str, access_token: str) -> Dict[str, Any]:
        """
        Get item details including View Count and Watch Count

        Args:
            item_id: eBay item ID
            access_token: OAuth access token

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
        # Use mock data if in mock mode
        if self._should_use_mock():
            return self._mock_get_item(item_id)

        headers = self._get_headers('GetItem', access_token)
        xml_body = self._build_request_xml('GetItem', {
            'ItemID': item_id,
            'DetailLevel': 'ReturnAll',
            'IncludeWatchCount': 'true',
        })

        response = self._make_request('POST', self.base_url, headers=headers, data=xml_body)
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

        def get_attr(path: str, attr: str, default: Any = None) -> Any:
            elem = item.find(path, ns)
            return elem.get(attr) if elem is not None else default

        return {
            'item_id': get_text('ns:ItemID'),
            'title': get_text('ns:Title'),
            'current_price': float(get_text('ns:SellingStatus/ns:CurrentPrice', 0)),
            'currency': get_attr('ns:SellingStatus/ns:CurrentPrice', 'currencyID', 'USD'),
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

    def get_my_ebay_selling(
        self,
        access_token: str,
        page_number: int = 1,
        entries_per_page: int = 200
    ) -> Dict[str, Any]:
        """
        Get list of active listings

        Args:
            access_token: OAuth access token
            page_number: Page number (1-indexed)
            entries_per_page: Number of items per page (max 200)

        Returns:
            {
                'items': [{'item_id': '123', 'title': '...', ...}, ...],
                'total_pages': 10,
                'total_entries': 1500,
            }
        """
        # Use mock data if in mock mode
        if self._should_use_mock():
            return self._mock_get_my_ebay_selling(page_number, entries_per_page)

        headers = self._get_headers('GetMyeBaySelling', access_token)
        xml_body = f"""<?xml version="1.0" encoding="utf-8"?>
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

        response = self._make_request('POST', self.base_url, headers=headers, data=xml_body)
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
        total_pages_elem = pagination.find('ns:TotalNumberOfPages', ns) if pagination else None
        total_entries_elem = pagination.find('ns:TotalNumberOfEntries', ns) if pagination else None

        return {
            'items': items,
            'total_pages': int(total_pages_elem.text) if total_pages_elem is not None else 1,
            'total_entries': int(total_entries_elem.text) if total_entries_elem is not None else len(items),
        }

    # ========== MOCK DATA METHODS ==========

    def _mock_get_item(self, item_id: str) -> Dict[str, Any]:
        """
        Generate mock item data for testing without eBay credentials

        Returns realistic-looking data with randomized metrics
        """
        # Use item_id as seed for consistent data
        random.seed(item_id)

        # Generate realistic categories
        categories = [
            ('11450', 'Clothing, Shoes & Accessories'),
            ('58058', 'Cell Phones & Accessories'),
            ('293', 'Computers/Tablets & Networking'),
            ('220', 'Toys & Hobbies'),
            ('625', 'Cameras & Photo'),
            ('267', 'Books, Movies & Music'),
            ('11233', 'Home & Garden'),
            ('888', 'Sporting Goods'),
            ('15032', 'Video Games & Consoles'),
            ('1', 'Collectibles'),
        ]

        category = random.choice(categories)

        # Generate realistic product names
        products = [
            "Vintage Watch Classic Design",
            "Wireless Bluetooth Headphones Pro",
            "Gaming Keyboard RGB Mechanical",
            "4K Action Camera Waterproof",
            "Smart Watch Fitness Tracker",
            "Laptop Stand Adjustable Aluminum",
            "LED Desk Lamp USB Rechargeable",
            "Phone Case Premium Leather",
            "External SSD 1TB Portable",
            "Coffee Maker Programmable 12-Cup",
        ]

        now = datetime.utcnow()
        start_time = now - timedelta(days=random.randint(1, 30))
        end_time = start_time + timedelta(days=30)

        return {
            'item_id': item_id,
            'title': random.choice(products),
            'current_price': round(random.uniform(9.99, 299.99), 2),
            'currency': 'USD',
            'view_count': random.randint(50, 500),
            'watch_count': random.randint(5, 50),
            'bid_count': random.randint(0, 20),
            'quantity': random.randint(1, 10),
            'quantity_sold': random.randint(0, 5),
            'listing_type': random.choice(['FixedPriceItem', 'Auction', 'StoresFixedPrice']),
            'listing_status': 'Active',
            'category_id': category[0],
            'category_name': category[1],
            'image_url': f'https://i.ebayimg.com/images/g/{item_id}/s-l300.jpg',
            'start_time': start_time.isoformat() + 'Z',
            'end_time': end_time.isoformat() + 'Z',
        }

    def _mock_get_my_ebay_selling(
        self,
        page_number: int = 1,
        entries_per_page: int = 200
    ) -> Dict[str, Any]:
        """
        Generate mock listing of active items

        Returns a paginated list of mock item IDs and titles
        """
        # Generate a consistent set of mock items (50 items total for testing)
        total_items = 50
        total_pages = (total_items + entries_per_page - 1) // entries_per_page

        # Calculate slice for current page
        start_idx = (page_number - 1) * entries_per_page
        end_idx = min(start_idx + entries_per_page, total_items)

        items = []
        for i in range(start_idx, end_idx):
            item_id = f"MOCK{1000000 + i}"
            # Generate consistent title based on item_id
            random.seed(item_id)
            products = [
                "Vintage Watch Classic Design",
                "Wireless Bluetooth Headphones Pro",
                "Gaming Keyboard RGB Mechanical",
                "4K Action Camera Waterproof",
                "Smart Watch Fitness Tracker",
                "Laptop Stand Adjustable Aluminum",
                "LED Desk Lamp USB Rechargeable",
                "Phone Case Premium Leather",
                "External SSD 1TB Portable",
                "Coffee Maker Programmable 12-Cup",
            ]
            items.append({
                'item_id': item_id,
                'title': random.choice(products),
            })

        return {
            'items': items,
            'total_pages': total_pages,
            'total_entries': total_items,
        }
