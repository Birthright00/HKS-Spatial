import json
import os
import argparse
import asyncio
from urllib.parse import urlparse
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# Semaphore to limit concurrent LLM API calls (avoid rate limits)
LLM_SEMAPHORE = asyncio.Semaphore(5)  # Max 5 concurrent LLM calls


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


async def find_verified_sellers_async(product_description, product_type="furniture", location="Singapore", target_count=10):
    """
    Async version: Find verified sellers with PARALLEL URL verification.
    This is 2-3x faster than the sequential version.
    """
    try:
        from webpage_analyzer import WebpageAnalyzer

        analyzer = WebpageAnalyzer()

        # Create more specific search queries based on product type
        query = f"buy {product_description} {location}"
        results = search_with_duckduckgo(query, num_results=target_count * 2)

        if not results:
            print("[X] No search results found")
            return [], 0

        # STRATEGY 2: Verify URLs in parallel
        async def verify_single_url(url):
            """Verify a single URL asynchronously with rate limiting"""
            try:
                # Use semaphore to limit concurrent LLM calls
                async with LLM_SEMAPHORE:
                    # Run the sync function in executor to avoid blocking
                    loop = asyncio.get_event_loop()
                    is_selling, reason = await loop.run_in_executor(
                        None,
                        analyzer.verify_url_sells_product,
                        url, product_description, product_type, location
                    )
                    if is_selling:
                        return {'url': url, 'reason': reason}
                    return None
            except Exception as e:
                print(f"[X] Error verifying {url}: {e}")
                return None

        # Process all URLs in parallel (with semaphore limiting concurrency)
        verification_tasks = [verify_single_url(url) for url in results]
        verification_results = await asyncio.gather(*verification_tasks, return_exceptions=True)

        # Filter out None results and exceptions
        verified_sellers = [
            result for result in verification_results
            if result and not isinstance(result, Exception)
        ]

        # Limit to target count
        verified_sellers = verified_sellers[:target_count]

        return verified_sellers, len(results)
    except Exception as e:
        print(f"[X] Verification failed: {e}")
        return [], 0


def refine_search_query(original_query, product_type, previous_attempts):
    """Use LLM to refine search query when no results are found"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("[X] OpenAI API key not configured")
        return None
    try:
        client = OpenAI(api_key=api_key)

        attempts_str = ", ".join([f'"{q}"' for q in previous_attempts])

        prompt = f"""The search query "{original_query}" (product type: {product_type}) did not return any valid sellers.

Previous attempts that failed: {attempts_str}

Please provide an alternative search query that:
1. Is BROADER or uses SYNONYMS (don't just reorder words)
2. Uses more common/general terms consumers actually search for
3. Removes overly specific details if present
4. Keeps the core product type and essential attributes

STRATEGIES:
- Use color synonyms: "burgundy" → "red", "beige" → "cream/tan", "muted" → "neutral"
- Simplify materials: "slip-resistant vinyl" → "vinyl flooring"
- Broaden categories: "LED recessed downlights" → "LED ceiling lights" → "ceiling lights"
- Use alternatives: "wall art" → "wall decor" or "framed prints"
- Try different phrasings: "closed storage units" → "storage cabinets" or "storage furniture"

Return ONLY the new search query (3-5 words, no explanation):

Examples:
- Original: "burgundy sofa" → Alternative: "red sofa"
- Original: "slip-resistant vinyl beige" → Alternative: "vinyl flooring cream"
- Original: "simple wall art muted tones" → Alternative: "wall decor neutral"
- Original: "LED recessed downlights" → Alternative: "LED ceiling lights"
- Original: "closed storage units" → Alternative: "storage cabinets"""

        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )

        refined_query = completion.choices[0].message.content.strip().strip('"')
        return refined_query
    except Exception as e:
        print(f"[X] Query refinement failed: {e}")
        return None


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
  → NEEDS_PURCHASE: YES | PRODUCT_TYPE: furniture | SEARCH_QUERY: storage units

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

            # Search for sellers with retry mechanism
            verified_sellers = []
            max_retries = 3
            current_query = search_query
            attempted_queries = [search_query]

            for attempt in range(max_retries):
                verified_sellers, _ = find_verified_sellers(current_query, product_type, location, target_verified)

                if verified_sellers:
                    print(f"  [OK] Found {len(verified_sellers)} sellers")
                    break
                else:
                    if attempt < max_retries - 1:
                        print(f"  [X] No verified sellers found, refining query...")
                        # Ask LLM to refine the search query
                        refined_query = refine_search_query(current_query, product_type, attempted_queries)
                        if refined_query and refined_query not in attempted_queries:
                            current_query = refined_query
                            attempted_queries.append(refined_query)
                            print(f"  -> Retry {attempt + 1}/{max_retries - 1}: {current_query}")
                        else:
                            print(f"  [X] Could not generate new query variation")
                            break
                    else:
                        print(f"  [X] No verified sellers found after {max_retries} attempts")

            if verified_sellers:
                # Add website info to issue
                issue['Website name'] = [urlparse(s['url']).netloc.replace('www.', '') for s in verified_sellers]
                issue['Website link'] = [s['url'] for s in verified_sellers]
                # Store the successful query if it was refined
                if current_query != search_query:
                    issue['Search query used'] = current_query

        # Overwrite original JSON file
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"\n[OK] Updated {json_file}")

    except Exception as e:
        print(f"[X] Error: {e}")
