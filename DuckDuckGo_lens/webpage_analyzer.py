import requests
from bs4 import BeautifulSoup
import re
import os
from dotenv import load_dotenv
from openai import OpenAI
import json


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
        if not self.is_available() or not self.client:
            return None
        try:
            completion = self.client.chat.completions.create(
                extra_headers={
                    "HTTP-Referer": "https://github.com/furniture-finder",
                    "X-Title": "Furniture Finder"
                },
                model=self.model,
                messages=[{"role": "user", "content": prompt}]
            )
            return completion.choices[0].message.content
        except Exception as e:
            if "429" in str(e) or "rate" in str(e).lower():
                print(f"[X] Rate limited - Try switching models in webpage_analyzer.py line 20")
            return None


class WebpageAnalyzer:
    """Analyzes webpages to verify if they sell specific furniture"""

    def __init__(self):
        self.llm = OpenRouterLLM()
        if not self.llm.is_available():
            print("[X] OpenRouter API key not configured")
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
        page_content = self.fetch_page_content(url)
        if not page_content:
            return False, "Could not fetch page"
        if self.llm:
            return self.analyze_page_with_llm(page_content, furniture_description, url)
        return self.analyze_page_simple(page_content, furniture_description)


def filter_relevant_results(urls, furniture_description, max_analyze=10):
    analyzer = WebpageAnalyzer()
    relevant_urls = []
    for url in urls[:max_analyze]:
        is_selling, reason = analyzer.verify_url_sells_furniture(url, furniture_description)
        if is_selling:
            relevant_urls.append({'url': url, 'reason': reason})
    return relevant_urls