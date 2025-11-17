#!/usr/bin/env python3
"""
Script to recursively scrape Columbia College bulletin pages
Visits all links and extracts all text content from every page
"""

import requests
from bs4 import BeautifulSoup
import json
import time
from urllib.parse import urljoin, urlparse
from collections import deque
import re

def scrape_page(url, visited_urls):
    """
    Scrape a single bulletin page and extract all content
    
    Args:
        url: URL of the page to scrape
        visited_urls: Set of already visited URLs to avoid duplicates
        
    Returns:
        dict: Dictionary containing scraped content and links
    """
    if url in visited_urls:
        return None
    
    try:
        # Add headers to mimic a browser request
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        print(f"Scraping: {url}")
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract title
        title = soup.find('h1')
        title_text = title.get_text(strip=True) if title else "No title found"
        
        # Extract main content
        main_content = soup.find('main') or soup.find('div', class_='content') or soup.find('article')
        if not main_content:
            main_content = soup.find('body')
        
        # Extract ALL text content from the page
        full_text = ""
        if main_content:
            # Get all text directly - this captures everything
            full_text = main_content.get_text(separator=' ', strip=True)
            # Clean up excessive whitespace
            full_text = re.sub(r'\s+', ' ', full_text).strip()
        
        # Extract all links on the page
        links = []
        base_domain = urlparse(url).netloc
        base_path = urlparse(url).path.rsplit('/', 1)[0] if '/' in urlparse(url).path else ''
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            full_url = urljoin(url, href)
            link_text = link.get_text(strip=True)
            
            # Only include links that are within the same domain and bulletin section
            parsed_link = urlparse(full_url)
            if parsed_link.netloc == base_domain:
                # Check if it's a Columbia College bulletin page
                if 'bulletin.columbia.edu' in full_url and 'columbia-college' in full_url:
                    links.append({
                        'text': link_text,
                        'url': full_url
                    })
        
        visited_urls.add(url)
        
        return {
            'url': url,
            'title': title_text,
            'full_text': full_text,
            'links': links,
            'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return None
    except Exception as e:
        print(f"Error parsing {url}: {e}")
        return None

def scrape_bulletin_recursive(start_url, output_file='columbia_college_2026.json', max_pages=1000):
    """
    Recursively scrape all Columbia College bulletin pages
    
    Args:
        start_url: Starting URL to begin scraping
        output_file: Output JSON file path
        max_pages: Maximum number of pages to scrape (safety limit)
    """
    print(f"Starting recursive scrape from: {start_url}")
    print(f"Maximum pages: {max_pages}\n")
    
    visited_urls = set()
    pages_data = []
    url_queue = deque([start_url])
    pages_scraped = 0
    
    # Try to load existing data to resume scraping
    try:
        with open(output_file, 'r', encoding='utf-8') as f:
            existing_data = json.load(f)
            visited_urls = set(page['url'] for page in existing_data.get('pages', []))
            pages_data = existing_data.get('pages', [])
            pages_scraped = len(pages_data)
            print(f"Resuming from existing file: {pages_scraped} pages already scraped")
            print(f"Already visited {len(visited_urls)} URLs\n")
            
            # Re-add all links from existing pages to the queue
            for page in pages_data:
                for link in page.get('links', []):
                    link_url = link['url']
                    if link_url not in visited_urls and link_url not in url_queue:
                        url_queue.append(link_url)
            print(f"Added {len(url_queue)} URLs from existing pages to queue\n")
    except FileNotFoundError:
        print("No existing file found, starting fresh\n")
    except json.JSONDecodeError:
        print("Existing file is corrupted, starting fresh\n")
    
    while url_queue and pages_scraped < max_pages:
        current_url = url_queue.popleft()
        
        if current_url in visited_urls:
            continue
        
        # Scrape the current page
        page_data = scrape_page(current_url, visited_urls)
        
        if page_data:
            pages_data.append(page_data)
            pages_scraped += 1
            
            # Add new links to the queue
            for link in page_data['links']:
                link_url = link['url']
                # Only add if we haven't visited it and it's not already in queue
                if link_url not in visited_urls and link_url not in url_queue:
                    url_queue.append(link_url)
            
            print(f"  ✓ Scraped page {pages_scraped}: {page_data['title']}")
            print(f"    Found {len(page_data['links'])} links, {len(page_data['full_text'])} characters of text")
            print(f"    Queue size: {len(url_queue)}\n")
            
            # Small delay to be respectful to the server
            time.sleep(0.5)
    
    # Save all scraped data to JSON
    output_data = {
        'start_url': start_url,
        'total_pages': len(pages_data),
        'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S'),
        'pages': pages_data
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*80}")
    print(f"Scraping complete!")
    print(f"Total pages scraped: {len(pages_data)}")
    print(f"Saved to: {output_file}")
    print(f"{'='*80}")
    
    # Also create a summary text file
    txt_file = output_file.replace('.json', '_summary.txt')
    with open(txt_file, 'w', encoding='utf-8') as f:
        f.write(f"Columbia College Bulletin Scrape Summary\n")
        f.write(f"{'='*80}\n\n")
        f.write(f"Start URL: {start_url}\n")
        f.write(f"Total Pages: {len(pages_data)}\n")
        f.write(f"Scraped At: {output_data['scraped_at']}\n\n")
        f.write(f"{'='*80}\n\n")
        
        for i, page in enumerate(pages_data, 1):
            f.write(f"\n{'='*80}\n")
            f.write(f"PAGE {i}: {page['title']}\n")
            f.write(f"URL: {page['url']}\n")
            f.write(f"{'='*80}\n\n")
            f.write(f"{page['full_text']}\n\n")
    
    print(f"Summary text file saved to: {txt_file}")

if __name__ == "__main__":
    # Starting URL
    url = "https://bulletin.columbia.edu/columbia-college/"
    
    # Recursively scrape all pages
    scrape_bulletin_recursive(url, output_file='columbia_college_2026.json', max_pages=1000)
    
    print("\nDone!")

