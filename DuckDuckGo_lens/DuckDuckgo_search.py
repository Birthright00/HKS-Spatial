import json
import os
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


def find_verified_furniture_sellers(furniture_description, location="Singapore", target_count=10):
    try:
        from webpage_analyzer import WebpageAnalyzer

        analyzer = WebpageAnalyzer()
        verified_sellers = []
        query = f"buy {furniture_description} {location} furniture store"
        results = search_with_duckduckgo(query, num_results=target_count * 2)

        if not results:
            print("[X] No search results found")
            return [], 0

        for url in results:
            if len(verified_sellers) >= target_count:
                break
            is_selling, reason = analyzer.verify_url_sells_furniture(url, furniture_description)
            if is_selling:
                verified_sellers.append({'url': url, 'reason': reason})

        return verified_sellers, len(results)
    except Exception as e:
        print(f"[X] Verification failed: {e}")
        return [], 0


def extract_search_query(recommendation):
    """Use LLM to extract furniture search query from recommendation"""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("[X] OpenRouter API key not configured")
        return None
    try:
        client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
        prompt = f"""Extract the furniture item to search for from this recommendation.

Recommendation: "{recommendation}"

Return ONLY the furniture item name in a simple, searchable format (e.g., "solid color rug", "burgundy sofa", "light filtering blinds").
Keep it under 8 words. Do not include brand names or specific measurements."""

        completion = client.chat.completions.create(
            model="openai/gpt-oss-20b:free",
            messages=[{"role": "user", "content": prompt}],
            extra_headers={
                "HTTP-Referer": "https://github.com/furniture-finder",
                "X-Title": "Furniture Finder"
            }
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        print(f"[X] LLM extraction failed: {e}")
        return None


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
    json_file = "interior2_analysis_20251122_102657.json"
    location = "Singapore"
    target_verified = 5

    try:
        # Read JSON file
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Process each issue
        for i, issue in enumerate(data.get('issues', []), 1):
            recommendation = issue.get('recommendation', '')

            # Skip if already has website info
            if 'Website name' in issue and 'Website link' in issue:
                print(f"[{i}] {issue['item']} - Already processed, skipping")
                continue

            if not recommendation:
                continue

            print(f"\n[{i}/{len(data['issues'])}] Processing: {issue['item']}")

            # Extract search query using LLM
            search_query = extract_search_query(recommendation)
            if not search_query:
                print(f"[X] Could not extract search query")
                continue

            print(f"  -> Searching: {search_query}")

            # Search for furniture
            verified_sellers, _ = find_verified_furniture_sellers(search_query, location, target_verified)

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
