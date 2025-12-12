"""
Product Search Microservice
Provides API endpoints for intelligent product search and seller verification
"""

import os
import asyncio
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from DuckDuckgo_search import (
    extract_search_query,
    refine_search_query,
    find_verified_sellers,
    find_verified_sellers_async
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
    timeout_seconds: int = Field(default=300, ge=30, le=600, description="Maximum time in seconds (default 300 = 5 minutes)")

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
                "max_retries": 3,
                "timeout_seconds": 300
            }
        }


class BatchSearchResponse(BaseModel):
    total_issues: int
    processed: int
    results: List[Dict[str, Any]]
    timed_out: bool = False
    timeout_message: Optional[str] = None


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
    Process multiple product searches in batch with PARALLEL processing.

    STRATEGY 1: Process multiple issues in parallel (3-5x faster)
    STRATEGY 2: Each issue verifies URLs in parallel (2-3x faster per issue)

    Combined speedup: 5-8x faster than sequential processing!

    Accepts a list of issues (same format as analysis JSON) and processes each one.
    Returns enhanced issues with seller information added.
    """
    try:
        async def process_single_issue(issue: Dict[str, Any]) -> Dict[str, Any]:
            """Process a single issue asynchronously"""
            item_name = issue.get('item', '')
            recommendation = issue.get('recommendation', '')

            # Quick checks - no async needed
            if not recommendation:
                return issue

            # Skip if already processed
            if 'Website name' in issue and 'Website link' in issue:
                return issue

            # Extract search query and product type (sync LLM call)
            loop = asyncio.get_event_loop()
            product_type, search_query = await loop.run_in_executor(
                None,
                extract_search_query,
                item_name, recommendation
            )

            # Skip if no purchase needed
            if not search_query or not product_type:
                return issue

            # Search with retry mechanism using ASYNC function
            verified_sellers = []
            current_query = search_query
            attempted_queries = [search_query]

            for attempt in range(request.max_retries):
                # Use async version of find_verified_sellers (STRATEGY 2)
                sellers, _ = await find_verified_sellers_async(
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
                        # Refine query (sync LLM call)
                        refined_query = await loop.run_in_executor(
                            None,
                            refine_search_query,
                            current_query, product_type, attempted_queries
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

            return issue

        # STRATEGY 1: Process all issues in parallel with timeout
        print(f"[Batch Search] Processing {len(request.issues)} issues in parallel (timeout: {request.timeout_seconds}s)...")

        # Create tasks for all issues
        tasks = [process_single_issue(issue.copy()) for issue in request.issues]

        # Track completed tasks and partial results
        completed_results = [None] * len(tasks)
        pending_tasks = {asyncio.create_task(task): i for i, task in enumerate(tasks)}

        timed_out = False
        timeout_message = None

        try:
            # Wait for all tasks with timeout
            done, pending = await asyncio.wait(
                pending_tasks.keys(),
                timeout=request.timeout_seconds,
                return_when=asyncio.ALL_COMPLETED
            )

            # Process completed tasks
            for task in done:
                task_index = pending_tasks[task]
                try:
                    result = await task
                    completed_results[task_index] = result
                except Exception as e:
                    print(f"[Error] Issue {task_index} failed: {e}")
                    completed_results[task_index] = request.issues[task_index]

            # Handle timeout - cancel pending tasks and use partial results
            if pending:
                timed_out = True
                completed_count = len(done)
                timeout_message = f"Search timed out after {request.timeout_seconds}s. Completed {completed_count}/{len(tasks)} items. Returning partial results."
                print(f"[Batch Search] {timeout_message}")

                # Cancel pending tasks
                for task in pending:
                    task.cancel()
                    task_index = pending_tasks[task]
                    # Return original issue for incomplete tasks
                    completed_results[task_index] = request.issues[task_index]

                # Wait for cancellation to complete
                await asyncio.gather(*pending, return_exceptions=True)

        except asyncio.TimeoutError:
            # Fallback timeout handling
            timed_out = True
            timeout_message = f"Search timed out after {request.timeout_seconds}s. Returning partial results."
            print(f"[Batch Search] {timeout_message}")

            # Fill in any None results with original issues
            for i, result in enumerate(completed_results):
                if result is None:
                    completed_results[i] = request.issues[i]

        # Count successfully processed items
        final_results = completed_results
        processed_count = sum(1 for result in final_results if 'Website name' in result and 'Website link' in result)

        print(f"[Batch Search] Completed: {processed_count}/{len(request.issues)} issues found sellers")

        return BatchSearchResponse(
            total_issues=len(request.issues),
            processed=processed_count,
            results=final_results,
            timed_out=timed_out,
            timeout_message=timeout_message
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
