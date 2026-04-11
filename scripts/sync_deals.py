import os
import json
import time
import requests
from dotenv import load_dotenv

# Load API key from .env file
load_dotenv()
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
RAPIDAPI_HOST = "real-time-amazon-data.p.rapidapi.com"

CONFIG_PATH = "config/products.json"
OUTPUT_PATH = "data/deals.json"

def fetch_amazon_deal(query):
    url = f"https://{RAPIDAPI_HOST}/search"
    querystring = {"query": query, "country": "IN", "category_id": "aps"}
    
    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": RAPIDAPI_HOST
    }

    try:
        response = requests.get(url, headers=headers, params=querystring)
        response.raise_for_status()
        data = response.json()
        
        if data.get("status") == "OK" and data.get("data", {}).get("products"):
            # Get the first product match
            product = data["data"]["products"][0]
            
            # Extract and clean price data
            price_str = product.get("product_price", "0").replace("₹", "").replace(",", "")
            original_price_str = product.get("product_original_price", price_str).replace("₹", "").replace(",", "")
            
            try:
                sale_price = float(price_str)
                original_price = float(original_price_str)
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
                "rating": float(product.get("product_star_rating", 0) or 0),
                "ratings": int(product.get("product_num_ratings", 0) or 0),
                "img": product.get("product_photo"),
                "url": product.get("product_url")
            }
    except Exception as e:
        print(f"Error fetching {query}: {e}")
    return None

def main():
    if not RAPIDAPI_KEY:
        print("Error: RAPIDAPI_KEY not found in environment variables.")
        return

    # Create directories if they don't exist
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    with open(CONFIG_PATH, "r") as f:
        config = json.load(f)

    deals = []
    
    # Process Amazon India deals
    for item in config.get("amazon_india", []):
        print(f"Syncing: {item['name']}...")
        result = fetch_amazon_deal(item["search_query"])
        
        if result:
            # Merge with config data (preserving ID and Affiliate Link)
            deal = {
                "id": item["id"],
                "title": result["title"],
                "store": "Amazon",
                "storeKey": "amazon",
                "category": "Auto-Updated",
                "catKey": "general",
                "img": result["img"],
                "originalPrice": result["originalPrice"],
                "salePrice": result["salePrice"],
                "discount": result["discount"],
                "rating": result["rating"],
                "ratings": result["ratings"],
                "badges": ["Live Price", "Verified"],
                "affiliateLink": item["affiliate_link"],
                "addedAt": int(time.time() * 1000)
            }
            deals.append(deal)
        else:
            print(f"Skipping {item['name']} due to fetch error.")

    # Save to JSON
    with open(OUTPUT_PATH, "w") as f:
        json.dump(deals, f, indent=4)
        
    print(f"Successfully synced {len(deals)} deals to {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
