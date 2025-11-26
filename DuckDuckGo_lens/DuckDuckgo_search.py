import json
import os
import argparse
from urllib.parse import urlparse
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


def search_with_duckduckgo(query, num_results=20):
    try:
        from ddgs import DDGS
        with DDGS() as ddgs:
            return [r.get('href') or r.get('link') for r in ddgs.text(query, max_results=num_results) if r.get('href') or r.get('link')]
    except Exception as e:
        print(f"[X] Search failed: {e}")
        return []


def find_verified_sellers(product_description, product_type="furniture", location="Singapore", target_count=10):
    """Find verified sellers for any product type (furniture, lighting, wall art, etc.)"""
    try:
        from webpage_analyzer import WebpageAnalyzer

        analyzer = WebpageAnalyzer()
        verified_sellers = []

        # Create more specific search queries based on product type
        query = f"buy {product_description} {location}"
        results = search_with_duckduckgo(query, num_results=target_count * 2)

        if not results:
            print("[X] No search results found")
            return [], 0

        for url in results:
            if len(verified_sellers) >= target_count:
                break
            is_selling, reason = analyzer.verify_url_sells_product(url, product_description, product_type, location)
            if is_selling:
                verified_sellers.append({'url': url, 'reason': reason})

        return verified_sellers, len(results)
    except Exception as e:
        print(f"[X] Verification failed: {e}")
        return [], 0


def extract_search_query(item_name, recommendation):
    """Use LLM to extract product search query and type from recommendation"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("[X] OpenAI API key not configured")
        return None, None
    try:
        client = OpenAI(api_key=api_key)
        prompt = f"""Analyze this item and recommendation to determine if a product search is needed, and if so, what to search for.

Item: "{item_name}"
Recommendation: "{recommendation}"

CRITICAL FIRST STEP - Determine if this requires purchasing anything:
- If the recommendation is about REARRANGING, ORGANIZING, REMOVING, or REPOSITIONING existing items → NO PURCHASE NEEDED
- If it mentions specific actions like "paint", "install", "replace", "add" with a specific product → PURCHASE NEEDED

Based on the item and recommendation, provide:
1. Needs Purchase: YES or NO
2. Product Type: What category (only if purchase needed)
3. Search Query: Simple, consumer-friendly search terms (only if purchase needed)

SEARCH QUERY RULES (if purchase needed):
- Strip ALL technical specs: lux, Kelvin (K), watts, voltage, LRV values, exact measurements
- Strip unnecessary phrases: "for organization", "to enhance", "providing", "at"
- Keep ONLY: core product name + essential descriptors (color, material, basic function)
- Maximum 4-5 words, use common product names consumers actually search

Return your answer in this exact format:
NEEDS_PURCHASE: YES/NO
PRODUCT_TYPE: [category or NONE]
SEARCH_QUERY: [search terms or NONE]

Examples:
- "Rearrange furniture to create clear pathways"
  → NEEDS_PURCHASE: NO | PRODUCT_TYPE: NONE | SEARCH_QUERY: NONE

- "Remove unnecessary items and organize in closed storage units"
  → NEEDS_PURCHASE: YES | PRODUCT_TYPE: furniture | SEARCH_QUERY: closed storage units

- "Install LED ceiling lights providing 450 lux at 3000K"
  → NEEDS_PURCHASE: YES | PRODUCT_TYPE: lighting | SEARCH_QUERY: LED ceiling lights

- "Replace floor with slip-resistant vinyl in warm beige"
  → NEEDS_PURCHASE: YES | PRODUCT_TYPE: flooring | SEARCH_QUERY: slip-resistant vinyl beige

- "Repaint walls in warm cream (LRV 72) with matte finish"
  → NEEDS_PURCHASE: YES | PRODUCT_TYPE: paint | SEARCH_QUERY: warm cream paint matte

- "Replace sofa with burgundy fabric (LRV 20)"
  → NEEDS_PURCHASE: YES | PRODUCT_TYPE: furniture | SEARCH_QUERY: burgundy sofa"""

        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )

        response = completion.choices[0].message.content.strip()

        # Parse the response
        needs_purchase = None
        product_type = None
        search_query = None

        for line in response.split('\n'):
            if 'NEEDS_PURCHASE:' in line:
                needs_purchase = line.split('NEEDS_PURCHASE:')[1].strip().upper()
            elif 'PRODUCT_TYPE:' in line:
                product_type = line.split('PRODUCT_TYPE:')[1].strip()
                if product_type == "NONE":
                    product_type = None
            elif 'SEARCH_QUERY:' in line:
                search_query = line.split('SEARCH_QUERY:')[1].strip()
                if search_query == "NONE":
                    search_query = None

        # If no purchase needed, return None for both
        if needs_purchase == "NO":
            return None, None

        return product_type, search_query
    except Exception as e:
        print(f"[X] LLM extraction failed: {e}")
        return None, None


def save_to_json(verified_sellers, output_file='verified_sellers.json'):
    try:
        output_data = [
            {
                'website_name': urlparse(s['url']).netloc.replace('www.', ''),
                'website_link': s['url'],
                'reason': s['reason']
            } for s in verified_sellers
        ]
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        print(f"[OK] Saved {len(verified_sellers)} results to {output_file}")
    except Exception as e:
        print(f"[X] Failed to save JSON: {e}")


if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Search for furniture sellers using DuckDuckGo')
    parser.add_argument('json_file', help='Path to the JSON file to process')
    parser.add_argument('--location', default='Singapore', help='Location to search (default: Singapore)')
    parser.add_argument('--target', type=int, default=5, help='Number of verified sellers to find (default: 5)')

    args = parser.parse_args()

    json_file = args.json_file
    location = args.location
    target_verified = args.target

    try:
        # Read JSON file
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Process each issue
        for i, issue in enumerate(data.get('issues', []), 1):
            item_name = issue.get('item', '')
            recommendation = issue.get('recommendation', '')

            # Skip if already has website info
            if 'Website name' in issue and 'Website link' in issue:
                print(f"[{i}] {issue['item']} - Already processed, skipping")
                continue

            if not recommendation:
                continue

            print(f"\n[{i}/{len(data['issues'])}] Processing: {issue['item']}")

            # Extract search query and product type using LLM
            product_type, search_query = extract_search_query(item_name, recommendation)

            # If no purchase needed, skip searching
            if not search_query or not product_type:
                print(f"  -> No purchase required (rearrangement/organization only)")
                continue

            print(f"  -> Product Type: {product_type}")
            print(f"  -> Searching: {search_query}")

            # Search for sellers
            verified_sellers, _ = find_verified_sellers(search_query, product_type, location, target_verified)

            if verified_sellers:
                # Add website info to issue
                issue['Website name'] = [urlparse(s['url']).netloc.replace('www.', '') for s in verified_sellers]
                issue['Website link'] = [s['url'] for s in verified_sellers]
                print(f"  [OK] Found {len(verified_sellers)} sellers")
            else:
                print(f"  [X] No verified sellers found")

        # Overwrite original JSON file
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"\n[OK] Updated {json_file}")

    except Exception as e:
        print(f"[X] Error: {e}")
