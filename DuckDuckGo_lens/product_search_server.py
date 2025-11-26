"""
Product Search Microservice
Provides API endpoints for intelligent product search and seller verification
"""

import os
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from DuckDuckgo_search import (
    extract_search_query,
    refine_search_query,
    find_verified_sellers
)

load_dotenv()

app = FastAPI(
    title="Product Search Service",
    description="Intelligent product search with LLM-powered query refinement and seller verification",
    version="1.0.0"
)


# Request/Response Models
class SearchRequest(BaseModel):
    item_name: str = Field(..., description="Name of the item (e.g., 'Sofa', 'Wall art')")
    recommendation: str = Field(..., description="Recommendation text describing what to search for")
    location: str = Field(default="Singapore", description="Location to search for sellers")
    target_sellers: int = Field(default=5, ge=1, le=20, description="Number of verified sellers to find")
    max_retries: int = Field(default=3, ge=1, le=5, description="Maximum query refinement attempts")

    class Config:
        json_schema_extra = {
            "example": {
                "item_name": "Sofa",
                "recommendation": "Replace sofa with one upholstered in burgundy fabric (LRV 20).",
                "location": "Singapore",
                "target_sellers": 5,
                "max_retries": 3
            }
        }


class SellerInfo(BaseModel):
    website_name: str
    website_link: str
    reason: str


class SearchResponse(BaseModel):
    success: bool
    needs_purchase: bool
    product_type: Optional[str] = None
    original_query: Optional[str] = None
    final_query: Optional[str] = None
    attempted_queries: List[str] = []
    sellers: List[SellerInfo] = []
    message: str


class BatchSearchRequest(BaseModel):
    issues: List[Dict[str, Any]] = Field(..., description="List of issues from analysis JSON")
    location: str = Field(default="Singapore", description="Location to search for sellers")
    target_sellers: int = Field(default=5, ge=1, le=20, description="Number of verified sellers per item")
    max_retries: int = Field(default=3, ge=1, le=5, description="Maximum query refinement attempts")

    class Config:
        json_schema_extra = {
            "example": {
                "issues": [
                    {
                        "item": "Sofa",
                        "recommendation": "Replace sofa with burgundy fabric"
                    }
                ],
                "location": "Singapore",
                "target_sellers": 5,
                "max_retries": 3
            }
        }


class BatchSearchResponse(BaseModel):
    total_issues: int
    processed: int
    results: List[Dict[str, Any]]


# API Endpoints
@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "online",
        "service": "Product Search Service",
        "version": "1.0.0"
    }


@app.post("/search", response_model=SearchResponse)
async def search_product(request: SearchRequest):
    """
    Search for product sellers based on item and recommendation.

    This endpoint:
    1. Analyzes the recommendation to determine if purchase is needed
    2. Extracts product type and search query
    3. Searches for verified sellers
    4. Retries with refined queries if no results found

    Returns seller information and search metadata.
    """
    try:
        # Extract search query and product type
        product_type, search_query = extract_search_query(
            request.item_name,
            request.recommendation
        )

        # Check if purchase is needed
        if not search_query or not product_type:
            return SearchResponse(
                success=True,
                needs_purchase=False,
                message="No purchase required (rearrangement/organization only)"
            )

        # Search with retry mechanism
        verified_sellers = []
        current_query = search_query
        attempted_queries = [search_query]

        for attempt in range(request.max_retries):
            sellers, _ = find_verified_sellers(
                current_query,
                product_type,
                request.location,
                request.target_sellers
            )

            if sellers:
                verified_sellers = sellers
                break
            else:
                if attempt < request.max_retries - 1:
                    # Refine the search query
                    refined_query = refine_search_query(
                        current_query,
                        product_type,
                        attempted_queries
                    )
                    if refined_query and refined_query not in attempted_queries:
                        current_query = refined_query
                        attempted_queries.append(refined_query)
                    else:
                        break

        # Format seller information
        seller_list = [
            SellerInfo(
                website_name=seller['url'].split('/')[2].replace('www.', ''),
                website_link=seller['url'],
                reason=seller['reason']
            )
            for seller in verified_sellers
        ]

        return SearchResponse(
            success=True,
            needs_purchase=True,
            product_type=product_type,
            original_query=search_query,
            final_query=current_query,
            attempted_queries=attempted_queries,
            sellers=seller_list,
            message=f"Found {len(seller_list)} verified sellers" if seller_list else "No verified sellers found"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search/batch", response_model=BatchSearchResponse)
async def batch_search_products(request: BatchSearchRequest):
    """
    Process multiple product searches in batch.

    Accepts a list of issues (same format as analysis JSON) and processes each one.
    Returns enhanced issues with seller information added.
    """
    try:
        results = []
        processed_count = 0

        for issue in request.issues:
            item_name = issue.get('item', '')
            recommendation = issue.get('recommendation', '')

            if not recommendation:
                results.append(issue)
                continue

            # Skip if already processed
            if 'Website name' in issue and 'Website link' in issue:
                results.append(issue)
                continue

            # Extract search query and product type
            product_type, search_query = extract_search_query(item_name, recommendation)

            # Skip if no purchase needed
            if not search_query or not product_type:
                results.append(issue)
                continue

            # Search with retry mechanism
            verified_sellers = []
            current_query = search_query
            attempted_queries = [search_query]

            for attempt in range(request.max_retries):
                sellers, _ = find_verified_sellers(
                    current_query,
                    product_type,
                    request.location,
                    request.target_sellers
                )

                if sellers:
                    verified_sellers = sellers
                    break
                else:
                    if attempt < request.max_retries - 1:
                        refined_query = refine_search_query(
                            current_query,
                            product_type,
                            attempted_queries
                        )
                        if refined_query and refined_query not in attempted_queries:
                            current_query = refined_query
                            attempted_queries.append(refined_query)

            # Add seller info to issue
            if verified_sellers:
                issue['Website name'] = [s['url'].split('/')[2].replace('www.', '') for s in verified_sellers]
                issue['Website link'] = [s['url'] for s in verified_sellers]
                if current_query != search_query:
                    issue['Search query used'] = current_query
                processed_count += 1

            results.append(issue)

        return BatchSearchResponse(
            total_issues=len(request.issues),
            processed=processed_count,
            results=results
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Detailed health check with dependency verification"""
    try:
        # Check if OpenAI API key is configured
        api_key = os.getenv("OPENAI_API_KEY")
        api_configured = bool(api_key)

        return {
            "status": "healthy",
            "openai_configured": api_configured,
            "dependencies": {
                "openai": "available",
                "duckduckgo": "available",
                "webpage_analyzer": "available"
            }
        }
    except Exception as e:
        return {
            "status": "degraded",
            "error": str(e)
        }


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PRODUCT_SEARCH_SERVICE_PORT", 8005))

    print(f"Starting Product Search Service on port {port}")
    print(f"API Documentation: http://localhost:{port}/docs")

    uvicorn.run(app, host="0.0.0.0", port=port)
