from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
import time
import random
from datetime import datetime

# Configuration - Only working areas with custom page limits
AREAS = {
    'athens-center': {
        'url': 'https://www.spitogatos.gr/en/for_sale-homes/athens-center',
        'pages': 80  # Will get ~2400 listings
    },
    'athens-north': {
        'url': 'https://www.spitogatos.gr/en/for_sale-homes/athens-north',
        'pages': 80  # Will get ~2400 listings
    },
    'athens-south': {
        'url': 'https://www.spitogatos.gr/en/for_sale-homes/athens-south',
        'pages': 60  # Will get ~900 listings
    }
}

def setup_driver():
    """Setup Chrome driver with anti-detection measures"""
    chrome_options = Options()
    
    # Anti-detection measures
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # Make it look more human
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    # Uncomment this line if you want headless mode (no browser window)
    # chrome_options.add_argument('--headless')
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    # Additional anti-detection
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    return driver

def scrape_listing(article):
    """Extract data from a single listing element"""
    try:
        data = {}
        
        # Property Type and Size
        try:
            title = article.find_element(By.CSS_SELECTOR, 'h3.tile__title').text
            if ',' in title:
                parts = title.split(',')
                data['property_type'] = parts[0].strip()
                data['size'] = parts[1].strip() if len(parts) > 1 else None
            else:
                data['property_type'] = title
                data['size'] = None
        except:
            data['property_type'] = None
            data['size'] = None
        
        # Location
        try:
            data['location'] = article.find_element(By.CSS_SELECTOR, 'h3.tile__location').text
        except:
            data['location'] = None
        
        # Description
        try:
            data['description'] = article.find_element(By.CSS_SELECTOR, 'p.tile__description').text
        except:
            data['description'] = None
        
        # Price
        try:
            data['price'] = article.find_element(By.CSS_SELECTOR, 'p.price__text').text
        except:
            data['price'] = None
        
        # Floor, Bedrooms, Bathrooms
        data['floor'] = None
        data['bedrooms'] = None
        data['bathrooms'] = None
        
        try:
            info_items = article.find_elements(By.CSS_SELECTOR, 'ul.tile__info li')
            for item in info_items:
                title_attr = item.get_attribute('title').lower() if item.get_attribute('title') else ''
                text = item.text
                
                if 'floor' in title_attr:
                    data['floor'] = text
                elif 'bedroom' in title_attr:
                    data['bedrooms'] = ''.join(filter(str.isdigit, text))
                elif 'bathroom' in title_attr:
                    data['bathrooms'] = ''.join(filter(str.isdigit, text))
        except:
            pass
        
        # URL
        try:
            link = article.find_element(By.CSS_SELECTOR, 'a.tile__link')
            data['url'] = link.get_attribute('href')
        except:
            data['url'] = None
        
        return data
    except Exception as e:
        print(f"    Error extracting listing: {e}")
        return None

def scrape_page(driver, url):
    """Scrape a single page"""
    try:
        print(f"  Loading: {url}")
        driver.get(url)
        
        # Random human-like delay
        time.sleep(random.uniform(3, 6))
        
        # Scroll down slowly (human behavior)
        total_height = driver.execute_script("return document.body.scrollHeight")
        for i in range(1, 4):
            driver.execute_script(f"window.scrollTo(0, {total_height * i / 4});")
            time.sleep(random.uniform(0.5, 1.5))
        
        # Wait for listings to load
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "article.ordered-element"))
            )
        except:
            print("  ⚠️ No listings found or page didn't load properly")
            return []
        
        # Find all listings
        articles = driver.find_elements(By.CSS_SELECTOR, "article.ordered-element")
        print(f"  Found {len(articles)} listings")
        
        listings = []
        for article in articles:
            listing_data = scrape_listing(article)
            if listing_data and listing_data.get('url'):
                listings.append(listing_data)
        
        return listings
        
    except Exception as e:
        print(f"  Error scraping page: {e}")
        return []

def scrape_area(driver, area_name, base_url, pages_for_area):
    """Scrape multiple pages from one area"""
    print(f"\n{'='*70}")
    print(f"📍 SCRAPING AREA: {area_name.upper().replace('-', ' ')}")
    print(f"   Target: {pages_for_area} pages")
    print(f"{'='*70}")
    
    all_listings = []
    
    for page_num in range(1, pages_for_area + 1):
        if page_num == 1:
            url = base_url
        else:
            url = f"{base_url}/page_{page_num}"
        
        listings = scrape_page(driver, url)
        
        if not listings:
            print(f"  No listings found on page {page_num}. Stopping for this area.")
            break
        
        all_listings.extend(listings)
        print(f"  Total from {area_name}: {len(all_listings)} listings")
        
        # Human-like delay between pages
        delay = random.uniform(5, 10)
        print(f"  Waiting {delay:.1f}s...")
        time.sleep(delay)
        
        # Longer break every 10 pages
        if page_num % 10 == 0:
            long_delay = random.uniform(20, 40)
            print(f"  ⏸️  Longer break: {long_delay:.0f}s...")
            time.sleep(long_delay)
    
    print(f"✅ Finished {area_name}: {len(all_listings)} listings")
    return all_listings

def scrape_all_areas():
    """Main scraping function"""
    driver = setup_driver()
    all_data = []
    area_stats = {}
    
    try:
        for area_name, area_info in AREAS.items():
            print(f"\n🔄 Starting {area_name}...")
            
            area_listings = scrape_area(driver, area_name, area_info['url'], area_info['pages'])
            
            if area_listings:
                all_data.extend(area_listings)
                area_stats[area_name] = len(area_listings)
            
            # Break between areas
            if area_name != list(AREAS.keys())[-1]:
                break_time = random.uniform(30, 60)
                print(f"\n⏸️  BREAK: {break_time:.0f}s before next area...")
                time.sleep(break_time)
        
    finally:
        driver.quit()
        print("\n🔒 Browser closed")
    
    return all_data, area_stats

def save_to_csv(listings):
    """Save to CSV"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"athens_selenium_{timestamp}.csv"
    
    df = pd.DataFrame(listings)
    columns_order = ['property_type', 'size', 'price', 'bedrooms', 'bathrooms', 
                     'floor', 'location', 'description', 'url']
    columns_order = [col for col in columns_order if col in df.columns]
    df = df[columns_order]
    
    df.to_csv(filename, index=False, encoding='utf-8-sig')
    print(f"\n📁 Saved: {filename}")
    print(f"Total: {len(df)} properties")
    return filename

if __name__ == "__main__":
    print("="*70)
    print("SPITOGATOS SELENIUM SCRAPER (ANTI-DETECTION)")
    print("="*70)
    print("\n📍 Areas and pages to scrape:")
    total_expected = 0
    for i, (area, info) in enumerate(AREAS.items(), 1):
        expected = info['pages'] * 30
        total_expected += expected
        print(f"  {i}. {area.replace('-', ' ').title()}: {info['pages']} pages (~{expected} listings)")
    
    print(f"\n📊 Expected total: ~{total_expected} listings")
    print(f"⏱️  Estimated time: ~{int(sum(a['pages'] for a in AREAS.values()) * 10 / 60)} minutes")
    print(f"\n🚀 Starting scraper...")
    print(f"⚠️  A Chrome browser window will open - DON'T CLOSE IT!")
    print("\nStarting in 3 seconds... (Press Ctrl+C to cancel)\n")
    time.sleep(3)
    
    # Scrape
    all_listings, area_stats = scrape_all_areas()
    
    # Stats
    print("\n" + "="*70)
    print("📊 RESULTS")
    print("="*70)
    for area, count in area_stats.items():
        print(f"  {area.replace('-', ' ').title()}: {count}")
    print(f"\n  TOTAL: {len(all_listings)}")
    
    # Save
    if all_listings:
        save_to_csv(all_listings)
        print(f"\n✅ SUCCESS!")
    else:
        print("\n❌ No data collected")
