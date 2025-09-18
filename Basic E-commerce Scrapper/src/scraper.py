import requests
from bs4 import BeautifulSoup
import csv
import sys
import re
from urllib.parse import urljoin
import time
from collections import Counter

BASE_URL = "https://books.toscrape.com/"
RATING_MAP = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}
SLEEP_SECONDS = 0.2  # polite pause between page requests; set to 0 to disable

def fetch_page(url):
    """Download page HTML and return text (safe with basic error handling)."""
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        # Let requests guess the correct encoding (helps with weird characters)
        if resp.apparent_encoding:
            resp.encoding = resp.apparent_encoding
        return resp.text
    except requests.exceptions.Timeout:
        print("❌ Error: Request timed out.")
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        sys.exit(1)

def parse_products(html):
    """
    Parse a single page's HTML and return a list of rows:
      [title (str), price (float or ''), availability (str), rating (int or '')]
    """
    soup = BeautifulSoup(html, "html.parser")
    products = soup.find_all("article", class_="product_pod")
    results = []

    if not products:
        return results

    for product in products:
        try:
            # --- Title ---
            title_tag = product.h3.a
            title = title_tag.get("title", "").strip()
            if not title:
                # If there's no title we skip this product (title is essential)
                raise AttributeError("missing title")

            # --- Price (safe) ---
            price_el = product.find("p", class_="price_color")
            price = ""  # default blank
            if price_el and price_el.text:
                price_text = price_el.text.strip()
                # Remove any non-digit except decimal point (handles Â, £, whitespace, etc.)
                price_clean = re.sub(r"[^0-9.]", "", price_text)
                try:
                    price = float(price_clean) if price_clean else ""
                except ValueError:
                    # Leave price blank if conversion still fails
                    price = ""

            # --- Availability (normalize) ---
            avail_el = product.find("p", class_="instock availability")
            avail_text = avail_el.text.strip() if avail_el and avail_el.text else ""
            availability = "In Stock" if "in stock" in avail_text.lower() else "Out of Stock"

            # --- Rating (map word to number) ---
            rating_tag = product.find("p", class_="star-rating")
            rating_word = None
            if rating_tag:
                classes = rating_tag.get("class", [])
                # classes typically: ["star-rating", "Three"]
                rating_word = next((c for c in classes if c.lower() != "star-rating"), None)
            rating_num = RATING_MAP.get(rating_word, "")

            results.append([title, price, availability, rating_num])

        except AttributeError as e:
            print(f"⚠️ Skipping a product due to missing field: {e}")
            continue

    return results

def get_next_page(html, current_url):
    """Return full URL of the 'next' page or None if last page."""
    soup = BeautifulSoup(html, "html.parser")
    next_li = soup.find("li", class_="next")
    if not next_li:
        return None
    href = next_li.a["href"]
    return urljoin(current_url, href)

def save_to_csv(rows, filename="products.csv"):
    """Write CSV header + rows. Price may be blank for problematic entries."""
    if not rows:
        print("⚠️ No data to save.")
        return
    try:
        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Title", "Price (£)", "Availability", "Rating (1-5)"])
            writer.writerows(rows)
        print(f"✅ Saved {len(rows)} products to {filename}")
    except Exception as e:
        print(f"❌ Failed to save CSV: {e}")

def main():
    url = BASE_URL
    all_rows = []

    while url:
        print(f"🔄 Fetching: {url}")
        html = fetch_page(url)

        page_rows = parse_products(html)
        all_rows.extend(page_rows)

        next_url = get_next_page(html, url)
        if next_url:
            time.sleep(SLEEP_SECONDS)  # be polite
        url = next_url

    # Save CSV
    save_to_csv(all_rows)

    # --- Summary statistics ---
    total = len(all_rows)
    prices = [r[1] for r in all_rows if isinstance(r[1], (int, float))]
    ratings = [r[3] for r in all_rows if isinstance(r[3], int)]

    avg_price = round(sum(prices) / len(prices), 2) if prices else None
    avg_rating = round(sum(ratings) / len(ratings), 2) if ratings else None

    rating_counts = Counter(ratings)

    print("\n📊 Summary:")
    print(f"  • Total products collected: {total}")
    print(f"  • Products with valid price: {len(prices)}")
    print(f"  • Products with missing price: {total - len(prices)}")
    print(f"  • Average price (using valid prices): £{avg_price if avg_price is not None else 'N/A'}")
    print(f"  • Average rating (1-5, using known ratings): {avg_rating if avg_rating is not None else 'N/A'}")
    print("  • Rating distribution:")
    for star in range(1, 6):
        print(f"      {star} star: {rating_counts.get(star, 0)}")

if __name__ == "__main__":
    main()
