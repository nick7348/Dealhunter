import os
import json
import time
import requests
from dotenv import load_dotenv

load_dotenv()
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
RAPIDAPI_HOST = "real-time-amazon-data.p.rapidapi.com"

CATALOG_PATH = "config/catalog.json"
PRODUCTS_PATH = "config/products.json"
OUTPUT_PATH = "data/deals.json"


def fetch_amazon_deal(query):
    url = f"https://{RAPIDAPI_HOST}/search"
    querystring = {"query": query, "country": "IN", "category_id": "aps"}
    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": RAPIDAPI_HOST
    }
    try:
        response = requests.get(url, headers=headers, params=querystring, timeout=15)
        response.raise_for_status()
        data = response.json()
        if data.get("status") == "OK" and data.get("data", {}).get("products"):
            product = data["data"]["products"][0]
            price_str = product.get("product_price", "0").replace("₹", "").replace(",", "")
            orig_str = product.get("product_original_price", price_str).replace("₹", "").replace(",", "")
            try:
                sale_price = float(price_str)
                original_price = float(orig_str)
            except ValueError:
                sale_price = 0
                original_price = 0
            discount = 0
            if original_price > 0:
                discount = int(((original_price - sale_price) / original_price) * 100)
            return {
                "title": product.get("product_title"),
                "salePrice": sale_price,
                "originalPrice": original_price,
                "discount": discount,
                "rating": float(product.get("product_star_rating") or 0),
                "ratings": int(product.get("product_num_ratings") or 0),
                "img": product.get("product_photo"),
            }
    except Exception as e:
        print(f"  Error: {e}")
    return None


def main():
    if not RAPIDAPI_KEY:
        print("Error: RAPIDAPI_KEY not found. Using catalog as-is.")

    # Load master catalog (all 50 products)
    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    # Build a lookup dict by ID for fast updates
    catalog_by_id = {item["id"]: item for item in catalog}

    # Load the products to sync via API
    if RAPIDAPI_KEY:
        with open(PRODUCTS_PATH, "r", encoding="utf-8") as f:
            products_config = json.load(f)

        for item in products_config.get("amazon_india", []):
            print(f"Syncing: {item['name']}...")
            result = fetch_amazon_deal(item["search_query"])

            if result and item["id"] in catalog_by_id:
                entry = catalog_by_id[item["id"]]
                # Preserve affiliate link from config/catalog, update live data
                entry["title"] = result["title"] or entry["title"]
                entry["salePrice"] = result["salePrice"] or entry["salePrice"]
                entry["originalPrice"] = result["originalPrice"] or entry["originalPrice"]
                entry["discount"] = result["discount"] or entry["discount"]
                entry["rating"] = result["rating"] or entry["rating"]
                entry["ratings"] = result["ratings"] or entry["ratings"]
                if result["img"]:
                    entry["img"] = result["img"]
                entry["badges"] = ["Live Price", "Verified"]
                entry["addedAt"] = int(time.time() * 1000)
                print(f"  Updated: {entry['title'][:60]}...")
            else:
                print(f"  Skipped (no result or ID not in catalog).")
    else:
        print("Skipping API sync — loading catalog directly.")

    # Final list is the full catalog (now with updated entries where applicable)
    final_deals = list(catalog_by_id.values())

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(final_deals, f, indent=4, ensure_ascii=False)

    print(f"\nDone! {len(final_deals)} deals saved to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
