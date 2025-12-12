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
            # FIX: Add a timeout to the client to prevent indefinite hangs on API calls
            self.client = OpenAI(api_key=self.api_key, timeout=20.0)

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
                print(f"[!] Rate limited - Open AI usage limit reached")
            else:
                print(f"[!] OpenAI API error: {e}")
            return None


class WebpageAnalyzer:
    """Analyzes webpages to verify if they sell specific products"""

    def __init__(self):
        self.llm = OpenAILLM()
        if not self.llm.is_available():
            print("[!] OpenAI API key not configured")
            self.llm = None

    def fetch_page_content(self, url, max_length=5000):
        """
        Fetches page content with strict safety limits to prevent hanging
        on large files (PDFs) or slow streams.
        """
        try:
            # FIX 1: Use stream=True to inspect headers before downloading body
            # FIX 2: Split timeout (5s connect, 10s read)
            with requests.get(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}, 
                            timeout=(5, 10), stream=True) as response:
                
                # FIX 3: Fail fast if status is bad
                if response.status_code != 200:
                    return None

                # FIX 4: Check Content-Type. If it's a PDF, Image, or Video, abort immediately.
                content_type = response.headers.get('Content-Type', '').lower()
                if 'text/html' not in content_type:
                    # print(f"    [Skipping non-HTML: {content_type}]")
                    return None

                # FIX 5: Manual content reading with size limit (Max 50KB raw data)
                # This prevents hanging on huge files.
                content_chunks = []
                current_length = 0
                max_download_size = 50000 

                for chunk in response.iter_content(chunk_size=4096, decode_unicode=True):
                    if chunk:
                        content_chunks.append(chunk)
                        current_length += len(chunk)
                        if current_length > max_download_size:
                            break
                
                full_text = "".join(content_chunks)

                # Parse HTML
                soup = BeautifulSoup(full_text, 'html.parser')
                
                # Remove non-content tags
                for script in soup(["script", "style", "nav", "footer", "header", "svg", "noscript"]):
                    script.decompose()
                
                text = soup.get_text()
                
                # Clean up whitespace
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                cleaned_text = ' '.join(chunk for chunk in chunks if chunk)
                
                return cleaned_text[:max_length]

        except requests.exceptions.Timeout:
            # print(f"    [Timeout loading {url}]")
            return None
        except Exception as e:
            # print(f"    [Error loading {url}: {e}]")
            return None

    def analyze_page_with_llm(self, page_content, product_description, product_type, url, required_location="Singapore"):
        """Use LLM to analyze if page sells the specified product and serves the required location"""
        if not self.llm or not page_content:
            return False, "No LLM or content"

        # (Prompt remains the same as original)
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
NO - [reason: wrong location, wrong product, not a store, etc.]"""

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
            # Return specific reason so we know why it failed in logs
            return False, "Could not fetch page (Timeout/404/Not HTML)"
        
        if self.llm:
            return self.analyze_page_with_llm(page_content, product_description, product_type, url, location)
        
        return self.analyze_page_simple(page_content, product_description, product_type)