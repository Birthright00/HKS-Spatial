"""
Webpage Analyzer using OpenRouter LLM
Fetches webpage content and uses AI to verify if it sells the furniture
"""

import requests
from bs4 import BeautifulSoup
import re
import os
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()


class OpenRouterLLM:
    """OpenRouter API interface for LLM analysis"""

    def __init__(self, model="openai/gpt-oss-20b:free"):
        self.model = model
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.client = None

        if self.is_available():
            self.client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=self.api_key
            )

    def is_available(self):
        """Check if API key is configured"""
        if not self.api_key or self.api_key == "your_openrouter_api_key_here":
            return False
        return True

    def analyze(self, prompt):
        """Send prompt to OpenRouter and get response"""
        if not self.is_available() or not self.client:
            print("  [!] OpenRouter API key not configured")
            return None

        try:
            completion = self.client.chat.completions.create(
                extra_headers={
                    "HTTP-Referer": "https://github.com/furniture-finder",
                    "X-Title": "Furniture Finder"
                },
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            return completion.choices[0].message.content

        except Exception as e:
            error_msg = str(e)

            # Check for rate limiting
            if "429" in error_msg or "rate" in error_msg.lower():
                print(f"  [!] Rate limit: {error_msg[:100]}")
                print(f"  [!] Try switching models in webpage_analyzer.py (line 19)")
            # Check for timeout
            elif "timeout" in error_msg.lower():
                print(f"  [!] Request timeout - API took too long to respond")
            # Check for connection errors
            elif "connection" in error_msg.lower():
                print(f"  [!] Connection error - Check your internet connection")
            else:
                print(f"  [!] LLM error: {type(e).__name__}: {str(e)[:100]}")

            return None


class WebpageAnalyzer:
    """Analyzes webpages to verify if they sell specific furniture"""

    def __init__(self):
        self.llm = OpenRouterLLM()

        if not self.llm.is_available():
            print("[!] Warning: OpenRouter API key not configured. Page analysis will be basic.")
            print("[!] Add your API key to the .env file: OPENROUTER_API_KEY=your_key_here")
            self.llm = None

    def fetch_page_content(self, url, max_length=3000):
        """Fetch and extract text from a webpage"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')

                # Remove script and style elements
                for script in soup(["script", "style", "nav", "footer", "header"]):
                    script.decompose()

                # Get text
                text = soup.get_text()

                # Clean up whitespace
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                text = ' '.join(chunk for chunk in chunks if chunk)

                # Limit length
                return text[:max_length]

            else:
                return None

        except Exception as e:
            print(f"  [!] Could not fetch {url}: {str(e)[:50]}")
            return None

    def analyze_page_with_llm(self, page_content, furniture_description, url):
        """Use LLM to analyze if page sells the furniture"""
        if not self.llm or not page_content:
            return False, "No LLM or content"

        prompt = f"""You are analyzing a webpage to determine if it is an E-COMMERCE STORE selling "{furniture_description}" and ensure it is Singapore based.

IMPORTANT RULES:
- Only say YES if this is a STORE/SHOP where you can BUY the furniture
- Strictly ensure the STORE/SHOP sells the furniture, and not just an advertisment on the STORE/SHOP
- Say NO if this is: a blog, news article, sports team, company website, Wikipedia, social media, review site, or anything else that is NOT selling furniture
- The page MUST have products for sale with prices or "add to cart" buttons
- The page MUST be about FURNITURE, not sports teams, companies, or other topics

Webpage URL: {url}

Webpage Content (first 3000 characters):
{page_content}

Question: Is this an e-commerce store selling "{furniture_description}"?

Answer STRICTLY with this format:
YES - [reason] (only if it's actually selling the furniture)
NO - [reason] (for everything else including sports, companies, blogs, etc.)

Examples:
[YES] - IKEA product page showing wooden dining tables with prices
[YES] - Furniture store with wooden tables available for purchase
[NO] - This is the Winnipeg Jets hockey team website, not a furniture store
[NO] - This is a blog post about furniture design, not a store
[NO] - This is a company's About page, not selling furniture"""

        try:
            response = self.llm.analyze(prompt)

            if response:
                response = response.strip()
                # Check if response starts with YES
                is_selling = response.upper().startswith("YES")
                return is_selling, response
            else:
                return False, "LLM failed to respond"

        except Exception as e:
            return False, f"Error: {e}"

    def analyze_page_simple(self, page_content, furniture_description):
        """Simple keyword-based analysis (fallback when no LLM)"""
        if not page_content:
            return False, "No content"

        page_lower = page_content.lower()
        furniture_lower = furniture_description.lower()

        # Extract keywords from furniture description
        keywords = furniture_lower.split()

        # Check for e-commerce indicators
        ecommerce_words = ['buy', 'price', 'add to cart', 'shop', 'purchase', 'order', 'delivery', '$', 'SGD']
        has_ecommerce = any(word.lower() in page_lower for word in ecommerce_words)

        # Check if furniture keywords are present
        keyword_matches = sum(1 for keyword in keywords if keyword in page_lower)
        keyword_ratio = keyword_matches / len(keywords) if keywords else 0

        if has_ecommerce and keyword_ratio > 0.5:
            return True, f"Keywords match: {keyword_ratio:.0%}, E-commerce page"
        else:
            return False, f"Keywords match: {keyword_ratio:.0%}, No e-commerce indicators"

    def verify_url_sells_furniture(self, url, furniture_description):
        """
        Main method to verify if a URL actually sells the furniture

        Returns:
            tuple: (is_selling: bool, reason: str)
        """
        print(f"\n  [*] Analyzing: {url[:60]}...")

        # Fetch page content
        page_content = self.fetch_page_content(url)

        if not page_content:
            return False, "Could not fetch page"

        # Use LLM if available, otherwise use simple analysis
        if self.llm:
            is_selling, reason = self.analyze_page_with_llm(page_content, furniture_description, url)
            print(f"     {'[OK]' if is_selling else '[X]'} {reason}")
            return is_selling, reason
        else:
            is_selling, reason = self.analyze_page_simple(page_content, furniture_description)
            print(f"     {'[OK]' if is_selling else '[X]'} {reason} (basic analysis)")
            return is_selling, reason


def filter_relevant_results(urls, furniture_description, max_analyze=10):
    """
    Filter search results to only include pages that actually sell the furniture

    Args:
        urls (list): List of URLs from search
        furniture_description (str): What furniture we're looking for
        max_analyze (int): Maximum number of URLs to analyze

    Returns:
        list: Filtered list of relevant URLs
    """
    analyzer = WebpageAnalyzer()
    relevant_urls = []
    rejected_urls = []

    total_to_check = min(len(urls), max_analyze)

    for i, url in enumerate(urls[:max_analyze], 1):
        print(f"\n[{i}/{total_to_check}] Checking website...")
        is_selling, reason = analyzer.verify_url_sells_furniture(url, furniture_description)

        if is_selling:
            relevant_urls.append({
                'url': url,
                'reason': reason
            })
            print(f"      [OK] VERIFIED - This sells {furniture_description}")
        else:
            rejected_urls.append({
                'url': url,
                'reason': reason
            })
            print(f"      [X] REJECTED - {reason[:80]}")

    return relevant_urls


# Test the analyzer
if __name__ == "__main__":
    print("="*60)
    print("WEBPAGE ANALYZER TEST")
    print("="*60)

    # Test URLs
    test_urls = [
        "https://www.ikea.com/sg/en/cat/dining-tables-21825/",
        "https://www.furniture.com.sg/dining-tables",
    ]

    furniture = "wooden dining table"

    results = filter_relevant_results(test_urls, furniture, max_analyze=2)

    print("\n" + "="*60)
    print("VERIFIED SELLERS:")
    print("="*60)
    for i, result in enumerate(results, 1):
        print(f"{i}. {result['url']}")
        print(f"   Reason: {result['reason']}\n")
