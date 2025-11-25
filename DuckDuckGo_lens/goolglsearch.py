"""
Simplified Furniture Search with DuckDuckGo + AI Verification
Keeps searching until we find the required number of verified furniture sellers
"""



def search_with_duckduckgo(query, num_results=20):
    """Search using DuckDuckGo - no rate limiting issues"""
    try:
        from ddgs import DDGS

        print(f"[*] Searching DuckDuckGo: {query}")
        results = []

        with DDGS() as ddgs:
            search_results = ddgs.text(query, max_results=num_results)

            for result in search_results:
                url = result.get('href') or result.get('link')
                if url:
                    results.append(url)

        print(f"   Found {len(results)} search results\n")
        return results

    except ImportError:
        print("❌ Error: ddgs not installed")
        print("💡 Install it with: pip install ddgs")
        return []

    except Exception as e:
        print(f"❌ Error during search: {e}")
        return []


def find_verified_furniture_sellers(furniture_description, location="Singapore", target_count=10):
    """
    Search and verify until we find the target number of verified furniture sellers

    Args:
        furniture_description: What furniture to search for
        location: Where to search
        target_count: How many verified sellers we want

    Returns:
        List of verified seller URLs
    """
    from webpage_analyzer import WebpageAnalyzer

    analyzer = WebpageAnalyzer()
    verified_sellers = []
    all_checked_urls = set()

    # Search in batches until we have enough verified sellers
    batch_size = 20
    max_attempts = 3

    for attempt in range(1, max_attempts + 1):
        if len(verified_sellers) >= target_count:
            break

        print(f"\n{'='*60}")
        print(f"SEARCH BATCH {attempt}")
        print(f"{'='*60}")
        print(f"Goal: Find {target_count} verified furniture sellers")
        print(f"Currently have: {len(verified_sellers)} verified")
        print(f"Need: {target_count - len(verified_sellers)} more\n")

        # Create search query
        query = f"buy {furniture_description} {location} furniture store"

        # Search DuckDuckGo
        results = search_with_duckduckgo(query, num_results=batch_size)

        if not results:
            print("[X] No search results found")
            break

        # Filter out URLs we've already checked
        new_urls = [url for url in results if url not in all_checked_urls]

        if not new_urls:
            print("[!] No new URLs to check")
            break

        print(f"[AI] Verifying {len(new_urls)} new websites...\n")

        # Check each URL
        for i, url in enumerate(new_urls, 1):
            all_checked_urls.add(url)

            print(f"[{len(verified_sellers)}/{target_count}] Checking website {i}/{len(new_urls)}...")
            is_selling, reason = analyzer.verify_url_sells_furniture(url, furniture_description)

            if is_selling:
                verified_sellers.append({
                    'url': url,
                    'reason': reason
                })
                print(f"      [OK] VERIFIED #{len(verified_sellers)}")

                # Stop if we've reached target
                if len(verified_sellers) >= target_count:
                    print(f"\n[SUCCESS] Reached target of {target_count} verified sellers!")
                    break
            else:
                print(f"      [X] REJECTED - {reason[:60]}")

    return verified_sellers, len(all_checked_urls)


# Main execution
if __name__ == "__main__":
    furniture_description = "sofa with one upholstered in burgundy fabric"
    location = "Singapore"
    target_verified = 10  # We want 10 verified sellers

    print("="*60)
    print("INTELLIGENT FURNITURE FINDER")
    print("="*60)
    print(f"Looking for: {furniture_description}")
    print(f"Location: {location}")
    print(f"Target: {target_verified} verified furniture sellers")
    print("="*60)

    try:
        # Search and verify until we get target number
        verified_sellers, total_checked = find_verified_furniture_sellers(
            furniture_description,
            location,
            target_count=target_verified
        )

        # Final statistics
        print("\n" + "="*60)
        print("FINAL STATISTICS")
        print("="*60)
        print(f"[OK] Verified sellers found: {len(verified_sellers)}")
        print(f"[*] Total websites checked: {total_checked}")
        print(f"[X] Rejected: {total_checked - len(verified_sellers)}")
        if total_checked > 0:
            print(f"[%] Success rate: {(len(verified_sellers)/total_checked*100):.1f}%")

        # Display all verified sellers
        print("\n" + "="*60)
        print(f"{len(verified_sellers)} VERIFIED FURNITURE SELLERS")
        print("="*60)

        if verified_sellers:
            for i, seller in enumerate(verified_sellers, 1):
                print(f"\n{i}. {seller['url']}")
                print(f"   [OK] {seller['reason']}")
        else:
            print("\n[!] No verified furniture sellers found")
            print("[TIP] Try a different search query or location")

        print("\n" + "="*60)
        print(f"RESULT: {len(verified_sellers)}/{target_verified} verified sellers")
        print("="*60)

    except ImportError:
        print("\n[X] Error: webpage_analyzer.py not found")
        print("[TIP] Make sure webpage_analyzer.py is in the same folder")
    except Exception as e:
        print(f"\n[X] Error: {e}")
