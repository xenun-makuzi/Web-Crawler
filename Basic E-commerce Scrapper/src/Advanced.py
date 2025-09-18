import requests
from bs4 import BeautifulSoup
import csv
import re
from urllib.parse import urljoin

BASE_URL = "https://books.toscrape.com/"
OUTPUT_FILE = "books_pattern_scraped.csv"

def fetch_page(url):
    """Fetch page content safely"""
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        print(f"❌ Failed to fetch {url}: {e}")
        return None

def parse_products(html):
    """Extract product details using patterns, not class names"""
    soup = BeautifulSoup(html, "html.parser")
    products = soup.find_all("article")   # assume each product is inside <article>
    results = []

    for p in products:
        # --- Title ---
        title = p.find("h3").a.get("title") if p.find("h3") else "?"

        # --- Price (look for <p> containing £) ---
        price_tag = p.find("p", string=re.compile("£"))
        if price_tag:
            price_text = price_tag.get_text(strip=True)
            price = re.sub(r"[^0-9.]", "", price_text)  # clean to numbers only
        else:
            price = ""

        # --- Availability (look for "stock") ---
        avail_tag = p.find("p", string=re.compile("stock", re.I))
        availability = avail_tag.get_text(strip=True) if avail_tag else "?"

        # --- Rating (look for <p> with word rating in class name) ---
        rating = ""
        rating_tag = p.find("p", class_=re.compile("star-rating"))
        if rating_tag:
            classes = rating_tag.get("class", [])
            rating_word = next((c for c in classes if c.lower() != "star-rating"), None)
            rating = rating_word if rating_word else ""

        results.append([title, price, availability, rating])
    return results

def get_next_page(html, current_url):
    """Find the next page if available"""
    soup = BeautifulSoup(html, "html.parser")
    next_li = soup.find("li", class_="next")
    if not next_li:
        return None
    return urljoin(current_url, next_li.a["href"])

def save_to_csv(rows, filename=OUTPUT_FILE):
    """Save all data to CSV"""
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Title", "Price (£)", "Availability", "Rating"])
        writer.writerows(rows)
    print(f"✅ Saved {len(rows)} products to {filename}")

def main():
    url = BASE_URL
    all_rows = []

    while url:
        print(f"🔄 Fetching: {url}")
        html = fetch_page(url)
        if not html:
            break

        page_rows = parse_products(html)
        all_rows.extend(page_rows)

        url = get_next_page(html, url)

    save_to_csv(all_rows)

if __name__ == "__main__":
    main()
