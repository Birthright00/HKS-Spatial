import requests
from bs4 import BeautifulSoup
import re
import os
from dotenv import load_dotenv
from openai import OpenAI
import json


# Load environment variables
load_dotenv()


class OpenAILLM:
    """OpenAI API interface for LLM analysis"""

    def __init__(self, model="gpt-4o-mini"):
        self.model = model
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.client = None

        if self.is_available():
            self.client = OpenAI(api_key=self.api_key)

    def is_available(self):
        """Check if API key is configured"""
        if not self.api_key:
            return False
        return True

    def analyze(self, prompt):
        if not self.is_available() or not self.client:
            return None
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}]
            )
            return completion.choices[0].message.content
        except Exception as e:
            if "429" in str(e) or "rate" in str(e).lower():
                print(f"[X] Rate limited - Please check your OpenAI API usage")
            else:
                print(f"[X] OpenAI API error: {e}")
            return None


class WebpageAnalyzer:
    """Analyzes webpages to verify if they sell specific products"""

    def __init__(self):
        self.llm = OpenAILLM()
        if not self.llm.is_available():
            print("[X] OpenAI API key not configured")
            self.llm = None

    def fetch_page_content(self, url, max_length=3000):
        try:
            response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                for script in soup(["script", "style", "nav", "footer", "header"]):
                    script.decompose()
                text = soup.get_text()
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                return ' '.join(chunk for chunk in chunks if chunk)[:max_length]
            return None
        except:
            return None

    def analyze_page_with_llm(self, page_content, product_description, product_type, url, required_location="Singapore"):
        """Use LLM to analyze if page sells the specified product and serves the required location"""
        if not self.llm or not page_content:
            return False, "No LLM or content"

        prompt = f"""You are analyzing a webpage to determine if it is an E-COMMERCE STORE selling "{product_description}" (product type: {product_type}) and serves customers in {required_location}.

CRITICAL REQUIREMENTS:
1. MUST be a store that SELLS products (not blog/article/company website)
2. MUST sell the correct product type
3. MUST serve/ship to {required_location} (check for: country indicators, shipping info, currency, domain)

LOCATION VERIFICATION:
- Check URL domain (.sg = Singapore, .uk = UK, .com.sg = Singapore, etc.)
- Look for "Singapore", "SGD", "shipping to Singapore" in content
- Look for location indicators like "UK only", "United Kingdom", "£" (reject these)
- If unclear, check if they mention international shipping or {required_location} delivery

STORE VERIFICATION:
- Must have products for sale with prices or "add to cart" or contact for purchase
- Match the product type correctly:
  * "furniture": sofas, chairs, tables, storage units
  * "window covering": blinds, curtains, shutters, shades
  * "wall decor" or "art": paintings, prints, wall hangings
  * "lighting": lamps, light fixtures, LED lights, downlights
  * "flooring": vinyl, carpet, tiles, rugs
  * "paint": wall paint, interior paint

Webpage URL: {url}
Webpage Content (first 3000 characters):
{page_content}

Question: Is this an e-commerce store selling "{product_description}" ({product_type}) that serves {required_location}?

Answer STRICTLY with this format:
YES - [reason including location verification]
NO - [reason: wrong location, wrong product, not a store, etc.]

Examples:
[YES] - Singapore lighting shop (domain: .com.sg) selling LED ceiling lights with SGD prices
[YES] - Home decor store in Singapore with wall art available for purchase
[NO] - UK-based vinyl flooring store (.co.uk domain), does not ship to Singapore
[NO] - This is selling furniture, not lighting fixtures
[NO] - This is a blog about interior design, not selling anything"""

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

    def analyze_page_simple(self, page_content, product_description, product_type):
        """Simple keyword-based analysis (fallback when no LLM)"""
        if not page_content:
            return False, "No content"

        page_lower = page_content.lower()
        product_lower = product_description.lower()

        # Extract keywords from product description
        keywords = product_lower.split()

        # Check for e-commerce indicators
        ecommerce_words = ['buy', 'price', 'add to cart', 'shop', 'purchase', 'order', 'delivery', '$', 'SGD']
        has_ecommerce = any(word.lower() in page_lower for word in ecommerce_words)

        # Check if product keywords are present
        keyword_matches = sum(1 for keyword in keywords if keyword in page_lower)
        keyword_ratio = keyword_matches / len(keywords) if keywords else 0

        if has_ecommerce and keyword_ratio > 0.5:
            return True, f"Keywords match: {keyword_ratio:.0%}, E-commerce page"
        else:
            return False, f"Keywords match: {keyword_ratio:.0%}, No e-commerce indicators"

    def verify_url_sells_product(self, url, product_description, product_type="furniture", location="Singapore"):
        """Verify if a URL sells the specified product and serves the location"""
        page_content = self.fetch_page_content(url)
        if not page_content:
            return False, "Could not fetch page"
        if self.llm:
            return self.analyze_page_with_llm(page_content, product_description, product_type, url, location)
        return self.analyze_page_simple(page_content, product_description, product_type)

    # Keep backward compatibility with old function name
    def verify_url_sells_furniture(self, url, furniture_description):
        """Legacy function for backward compatibility"""
        return self.verify_url_sells_product(url, furniture_description, "furniture")


def filter_relevant_results(urls, furniture_description, max_analyze=10):
    analyzer = WebpageAnalyzer()
    relevant_urls = []
    for url in urls[:max_analyze]:
        is_selling, reason = analyzer.verify_url_sells_furniture(url, furniture_description)
        if is_selling:
            relevant_urls.append({'url': url, 'reason': reason})
    return relevant_urls