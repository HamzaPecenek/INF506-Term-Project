import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
from datetime import datetime

# Configuration
BASE_URL = "https://www.spitogatos.gr/en/for_sale-homes/athens-center"
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

def scrape_page(page_num):
    """Scrape a single page of listings"""
    try:
        if page_num == 1:
            url = BASE_URL
        else:
            url = f"{BASE_URL}/page_{page_num}"
        
        print(f"Scraping page {page_num}: {url}")
        
        response = requests.get(url, headers=HEADERS, timeout=30)
        
        if response.status_code == 404:
            print(f"Page {page_num} not found (404)")
            return None
        
        if response.status_code != 200:
            print(f"Error: Status code {response.status_code}")
            return None
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find all article elements with class "ordered-element"
        articles = soup.find_all('article', class_='ordered-element')
        
        print(f"Found {len(articles)} listings on page {page_num}")
        
        listings = []
        for article in articles:
            listing_data = scrape_listing(article)
            if listing_data and listing_data.get('url'):  # Only add if we have valid data
                listings.append(listing_data)
        
        return listings
    
    except requests.exceptions.RequestException as e:
        print(f"Request error on page {page_num}: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error on page {page_num}: {e}")
        return None

def scrape_multiple_pages(start_page=1, end_page=10):
    """Scrape multiple pages"""
    all_listings = []
    
    for page_num in range(start_page, end_page + 1):
        listings = scrape_page(page_num)
        
        if listings is None:
            print(f"Stopping at page {page_num}")
            break
        
        all_listings.extend(listings)
        print(f"Total listings so far: {len(all_listings)}")
        
        # Random delay between requests (2-5 seconds)
        delay = random.uniform(2, 5)
        print(f"Waiting {delay:.1f} seconds before next page...")
        time.sleep(delay)
    
    return all_listings

def save_to_csv(listings, filename=None):
    """Save listings to CSV"""
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"athens_properties_{timestamp}.csv"
    
    df = pd.DataFrame(listings)
    
    # Reorder columns
    columns_order = ['property_type', 'size', 'price', 'bedrooms', 'bathrooms', 
                     'floor', 'location', 'description', 'url']
    
    # Only include columns that exist
    columns_order = [col for col in columns_order if col in df.columns]
    df = df[columns_order]
    
    df.to_csv(filename, index=False, encoding='utf-8-sig')
    print(f"\nData saved to {filename}")
    print(f"Total properties: {len(df)}")
    return filename

# Main execution
if __name__ == "__main__":
    print("=" * 60)
    print("SPITOGATOS ATHENS SCRAPER")
    print("=" * 60)
    print()
    
    # Ask user for number of pages
    try:
        num_pages = int(input("How many pages do you want to scrape? (For 5000+ listings, try ~170 pages): "))
    except ValueError:
        print("Invalid input. Defaulting to 10 pages.")
        num_pages = 10
    
    print(f"\nStarting to scrape {num_pages} pages...")
    print("This may take a while. Please be patient.\n")
    
    # Scrape the data
    listings = scrape_multiple_pages(start_page=1, end_page=num_pages)
    
    # Save to CSV
    if listings:
        filename = save_to_csv(listings)
        print(f"\n✅ SUCCESS! Scraped {len(listings)} properties.")
        print(f"📁 File saved as: {filename}")
    else:
        print("\n❌ No data collected. Please check the website or try again.")