import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
from datetime import datetime

# Configuration - Multiple Athens areas
AREAS = {
    'athens-center': 'https://www.spitogatos.gr/en/for_sale-homes/athens-center',
    'athens-north': 'https://www.spitogatos.gr/en/for_sale-homes/athens-north',
    'athens-south': 'https://www.spitogatos.gr/en/for_sale-homes/athens-south',
    'athens-west': 'https://www.spitogatos.gr/en/for_sale-homes/athens-west',
    'piraeus': 'https://www.spitogatos.gr/en/for_sale-homes/piraeus'
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Connection': 'keep-alive',
}

def scrape_listing(article):
    """Extract data from a single listing article element"""
    try:
        data = {}
        
        # Property Type and Size (from title)
        title_elem = article.find('h3', class_='tile__title')
        if title_elem:
            title_text = title_elem.get_text(strip=True)
            data['title'] = title_text
            # Extract type and size (e.g., "Apartment, 101m²")
            if ',' in title_text:
                parts = title_text.split(',')
                data['property_type'] = parts[0].strip()
                data['size'] = parts[1].strip() if len(parts) > 1 else None
            else:
                data['property_type'] = title_text
                data['size'] = None
        
        # Location
        location_elem = article.find('h3', class_='tile__location')
        data['location'] = location_elem.get_text(strip=True) if location_elem else None
        
        # Description
        desc_elem = article.find('p', class_='tile__description')
        data['description'] = desc_elem.get_text(strip=True) if desc_elem else None
        
        # Price
        price_elem = article.find('p', class_='price__text')
        data['price'] = price_elem.get_text(strip=True) if price_elem else None
        
        # Floor, Bedrooms, Bathrooms
        info_list = article.find('ul', class_='tile__info')
        data['floor'] = None
        data['bedrooms'] = None
        data['bathrooms'] = None
        
        if info_list:
            list_items = info_list.find_all('li')
            for item in list_items:
                title_attr = item.get('title', '').lower()
                text = item.get_text(strip=True)
                
                if 'floor' in title_attr:
                    data['floor'] = text
                elif 'bedroom' in title_attr:
                    # Extract just the number
                    data['bedrooms'] = ''.join(filter(str.isdigit, text))
                elif 'bathroom' in title_attr:
                    # Extract just the number
                    data['bathrooms'] = ''.join(filter(str.isdigit, text))
        
        # Property URL
        link_elem = article.find('a', class_='tile__link')
        if link_elem and link_elem.get('href'):
            data['url'] = 'https://www.spitogatos.gr' + link_elem['href']
        else:
            data['url'] = None
        
        return data
    
    except Exception as e:
        print(f"Error extracting listing: {e}")
        return None

def scrape_page(base_url, page_num):
    """Scrape a single page of listings"""
    try:
        if page_num == 1:
            url = base_url
        else:
            url = f"{base_url}/page_{page_num}"
        
        print(f"  Scraping page {page_num}: {url}")
        
        response = requests.get(url, headers=HEADERS, timeout=30)
        
        if response.status_code == 404:
            print(f"  Page {page_num} not found (404) - end of listings")
            return None
        
        if response.status_code != 200:
            print(f"  Error: Status code {response.status_code}")
            return None
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find all article elements with class "ordered-element"
        articles = soup.find_all('article', class_='ordered-element')
        
        print(f"  Found {len(articles)} listings on page {page_num}")
        
        listings = []
        for article in articles:
            listing_data = scrape_listing(article)
            if listing_data and listing_data.get('url'):  # Only add if we have valid data
                listings.append(listing_data)
        
        return listings
    
    except requests.exceptions.RequestException as e:
        print(f"  Request error on page {page_num}: {e}")
        return None
    except Exception as e:
        print(f"  Unexpected error on page {page_num}: {e}")
        return None

def scrape_area(area_name, base_url, pages_per_area):
    """Scrape multiple pages from one area"""
    print(f"\n{'='*70}")
    print(f"📍 SCRAPING AREA: {area_name.upper().replace('-', ' ')}")
    print(f"{'='*70}")
    
    all_listings = []
    pages_scraped = 0
    
    for page_num in range(1, pages_per_area + 1):
        listings = scrape_page(base_url, page_num)
        
        if listings is None or len(listings) == 0:
            print(f"  No more listings found. Stopping for this area.")
            break
        
        all_listings.extend(listings)
        pages_scraped += 1
        print(f"  Total from {area_name}: {len(all_listings)} listings")
        
        # Random delay between requests (5-12 seconds)
        delay = random.uniform(5, 12)
        print(f"  Waiting {delay:.1f}s before next page...")
        time.sleep(delay)
        
        # Extra long pause every 10 pages
        if page_num % 10 == 0:
            long_delay = random.uniform(20, 40)
            print(f"  ⏸️  Taking a longer break ({long_delay:.0f}s)...")
            time.sleep(long_delay)
    
    print(f"\n✅ Finished {area_name}: {len(all_listings)} listings from {pages_scraped} pages")
    return all_listings

def scrape_all_areas(pages_per_area=50):
    """Scrape all Athens areas"""
    all_data = []
    area_stats = {}
    
    for area_name, base_url in AREAS.items():
        print(f"\n🔄 Starting {area_name}...")
        
        area_listings = scrape_area(area_name, base_url, pages_per_area)
        
        if area_listings:
            all_data.extend(area_listings)
            area_stats[area_name] = len(area_listings)
        
        # Long break between areas (30-60 seconds)
        if area_name != list(AREAS.keys())[-1]:  # Don't wait after last area
            break_time = random.uniform(30, 60)
            print(f"\n⏸️  BREAK: Waiting {break_time:.0f}s before next area...")
            time.sleep(break_time)
    
    return all_data, area_stats

def save_to_csv(listings, filename=None):
    """Save listings to CSV"""
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"athens_all_areas_{timestamp}.csv"
    
    df = pd.DataFrame(listings)
    
    # Reorder columns
    columns_order = ['property_type', 'size', 'price', 'bedrooms', 'bathrooms', 
                     'floor', 'location', 'description', 'url']
    
    # Only include columns that exist
    columns_order = [col for col in columns_order if col in df.columns]
    df = df[columns_order]
    
    df.to_csv(filename, index=False, encoding='utf-8-sig')
    print(f"\n📁 Data saved to {filename}")
    print(f"Total properties: {len(df)}")
    return filename

# Main execution
if __name__ == "__main__":
    print("="*70)
    print("SPITOGATOS ATHENS MULTI-AREA SCRAPER")
    print("="*70)
    print("\n📍 Areas to scrape:")
    for i, area in enumerate(AREAS.keys(), 1):
        print(f"  {i}. {area.replace('-', ' ').title()}")
    
    print("\n" + "="*70)
    
    # Ask user for pages per area
    try:
        pages = int(input("How many pages per area? (Recommended: 30-40 for ~1000 listings each): "))
    except ValueError:
        print("Invalid input. Using default: 30 pages per area.")
        pages = 30
    
    print(f"\n🚀 Will scrape {pages} pages from each of {len(AREAS)} areas")
    print(f"📊 Expected total: ~{pages * 30 * len(AREAS)} listings")
    print(f"⏱️  Estimated time: {int((pages * len(AREAS) * 8) / 60)} minutes")
    print("\nStarting in 3 seconds... (Press Ctrl+C to cancel)")
    time.sleep(3)
    
    # Scrape all areas
    all_listings, area_stats = scrape_all_areas(pages_per_area=pages)
    
    # Display statistics
    print("\n" + "="*70)
    print("📊 SCRAPING STATISTICS")
    print("="*70)
    for area, count in area_stats.items():
        print(f"  {area.replace('-', ' ').title()}: {count} listings")
    print(f"\n  TOTAL: {len(all_listings)} listings")
    
    # Save to CSV
    if all_listings:
        filename = save_to_csv(all_listings)
        print(f"\n✅ SUCCESS! Scraped {len(all_listings)} properties from {len(area_stats)} areas.")
        print(f"📁 File saved as: {filename}")
    else:
        print("\n❌ No data collected. Please check the website or try again later.")
