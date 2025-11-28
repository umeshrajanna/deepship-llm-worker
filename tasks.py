"""
LLM Worker Tasks
Handles deep search and report generation orchestration
"""

import json
import asyncio
from typing import Dict, List, Optional
from celery import Task
from celery.result import AsyncResult
from celery_app import celery_app
import redis

# Import the deep search generator
from deep_search import EnhancedMarkdownReportGenerator

# # Redis client for pub/sub progress updates
# redis_client = redis.Redis(
#     host='localhost',  # Update with your Redis host
#     port=6379,
#     db=0,
#     decode_responses=True
# )

import os

redis_client = redis.Redis(
    host=os.getenv('REDIS_HOST', 'localhost'),  # ✅ Use environment variable
    port=int(os.getenv('REDIS_PORT', 6379)),
    db=0,
    decode_responses=True,
    socket_connect_timeout=5,
    socket_timeout=5,
    retry_on_timeout=True
)
# Import scraper task signature for type hints
# from tasks import scrape_content_task  # This will be in scraper worker


# ============================================================================
# HELPER: Publish Progress Updates
# ============================================================================

def publish_progress(job_id: str, update: Dict):
    """Publish progress update to Redis pub/sub channel"""
    channel = f"job:{job_id}:progress"
    try:
        redis_client.publish(channel, json.dumps(update))
        print(f"[PROGRESS] Published to {channel}: {update.get('type')}")
    except redis.ConnectionError as e:
        # Don't crash if Redis pub/sub fails - just log it
        print(f"[PROGRESS] Failed to publish (non-fatal): {e}")
    except Exception as e:
        print(f"[PROGRESS] Failed to publish: {e}")

# ============================================================================
# HELPER: Call Scraper Worker and Wait for Results
# ============================================================================

async def call_scraper_and_wait(
    job_id: str,
    urls: List[str],
    search_query: str,
    original_query: str,
    timeout: int = 600
) -> List[Dict]:
    """
    Send URLs to scraper worker and wait for results
    
    Args:
        job_id: Job identifier
        urls: List of URLs to scrape
        search_query: The refined search query
        original_query: Original user query
        timeout: Max wait time in seconds
        
    Returns:
        List of scrape results
    """
    
    if not urls:
        print(f"[SCRAPER] No URLs provided, skipping scrape")
        return []
    
    print("=" * 80)
    print(f"🌐 CALLING SCRAPER WORKER")
    print("=" * 80)
    print(f"Job ID: {job_id}")
    print(f"URLs to scrape: {len(urls)}")
    print(f"Search Query: {search_query}")
    print(f"Original Query: {original_query}")
    print("-" * 80)
    
    # Log URLs being sent
    for i, url in enumerate(urls, 1):
        print(f"  {i}. {url}")
    print("=" * 80)
    
    try:
        # Send task to scraper worker queue
        # Task signature: scrape_content_task(job_id, urls, search_query, original_query)
        scrape_task = celery_app.send_task(
            'tasks.scrape_content_task',
            args=[job_id, urls, search_query, original_query],
            queue='scraper'
        )
        
        print(f"✅ Scraper task sent: {scrape_task.id}")
        print(f"⏳ Waiting for scraper results (timeout: {timeout}s)...")
        
        # Wait for scraper to complete
        # This blocks until scraper finishes or timeout
        scraped_results = scrape_task.get(timeout=timeout)
        
        print(f"✅ Received scraper results!")
        print(f"Result type: {type(scraped_results)}")
        
        # Parse results based on scraper's return format
        if isinstance(scraped_results, dict):
            # Scraper returns: {'data': {...}, 'urls_scraped': [...], ...}
            if 'data' in scraped_results and scraped_results['data']:
                actual_results = scraped_results['data'].get('results', [])
                print(f"✅ Parsed {len(actual_results)} scrape results from data field")
                return actual_results
            elif 'error' in scraped_results:
                print(f"❌ Scraper returned error: {scraped_results['error']}")
                return []
            else:
                print(f"⚠️ Unexpected scraper result format")
                return []
        
        elif isinstance(scraped_results, list):
            # Scraper returns results list directly
            print(f"✅ Received {len(scraped_results)} scrape results")
            return scraped_results
        
        else:
            print(f"❌ Unexpected result type: {type(scraped_results)}")
            return []
        
    except Exception as e:
        print(f"❌ Error calling scraper: {e}")
        print(f"   Job ID: {job_id}")
        print(f"   URLs: {len(urls)}")
        return []


# ============================================================================
# MAIN LLM WORKER TASK
# ============================================================================

@celery_app.task(
    bind=True,
    name='tasks.deep_search_task',
    max_retries=1,
    soft_time_limit=900,  # 15 minutes
    time_limit=960  # 16 minutes hard limit
)
def deep_search_task(
    self,
    job_id: str,
    query: str,
    conversation_history: Optional[List[Dict]] = None
):
    """
    Main deep search task - orchestrates the entire research pipeline
    
    Args:
        job_id: Unique job identifier
        query: User's search query
        conversation_history: Previous conversation context
        
    Returns:
        dict: Final results with markdown and metadata
    """
    
    print("=" * 80)
    print("🧠 LLM WORKER - DEEP SEARCH TASK STARTED")
    print("=" * 80)
    print(f"Job ID: {job_id}")
    print(f"Query: {query}")
    print(f"Conversation History: {len(conversation_history) if conversation_history else 0} messages")
    print("=" * 80)
    
    # Publish initial progress
    publish_progress(job_id, {
        "type": "started",
        "content": "Deep search initiated"
    })
    
    try:
        # Initialize the report generator
        generator = EnhancedMarkdownReportGenerator(
            enable_reasoning_capture=True,
            verbose=True,
            max_search_queries=10,
            max_urls_to_scrape=5,
            scrape_timeout=600,
            scrape_chunk_size=400,
            scrape_concurrency=10
        )
        
        # CRITICAL: Inject scraper callback function
        # This allows deep_search.py to call our scraper worker
        generator.scraper_callback = lambda urls, search_query, original_query: asyncio.run(
            call_scraper_and_wait(job_id, urls, search_query, original_query)
        )
        
        # CRITICAL: Inject progress callback function
        # This allows deep_search.py to publish progress updates
        generator.progress_callback = lambda update: publish_progress(job_id, update)
        
        print("✅ Generator initialized with callbacks")
        print("🚀 Starting develop_report...")
        
        # Run the async generator
        final_markdown = None
        analysis_summary = None
        
        async def run_development():
            nonlocal final_markdown, analysis_summary
            
            async for result in generator.develop_report(
                user_prompt=query,
                conversation_history=conversation_history,
                use_multi_stage=True,
                enable_scraping=True,
                return_conversation=True
            ):
                # Forward all progress updates to Redis pub/sub
                if result.get("type") in ["reasoning", "sources", "transformed_query"]:
                    publish_progress(job_id, result)
                
                elif result.get("type") == "markdown":
                    final_markdown = result.get("content")
                    print(f"✅ Markdown generated: {len(final_markdown)} characters")
                
                elif result.get("type") == "analysis_summary":
                    analysis_summary = result.get("content")
                    print(f"✅ Analysis summary generated")
                
                elif result.get("type") == "done":
                    print(f"✅ Development complete")
        
        # Execute the async function
        asyncio.run(run_development())
        
        if not final_markdown:
            raise Exception("No markdown generated")
        
        print("=" * 80)
        print("✅ DEEP SEARCH TASK COMPLETED")
        print("=" * 80)
        print(f"Job ID: {job_id}")
        print(f"Markdown length: {len(final_markdown)}")
        print(f"Analysis summary: {'Yes' if analysis_summary else 'No'}")
        print("=" * 80)
        
        # Publish final result
        publish_progress(job_id, {
            "type": "completed",
            "content": "Report generation complete"
        })
        
        # Return final results
        return {
            "job_id": job_id,
            "status": "completed",
            "markdown": final_markdown,
            "analysis_summary": analysis_summary,
            "conversation_history": generator.get_conversation_history(),
            "reasoning_logs": generator.reasoning_logs if generator.enable_reasoning_capture else []
        }
        
    except Exception as e:
        print("=" * 80)
        print("❌ DEEP SEARCH TASK FAILED")
        print("=" * 80)
        print(f"Job ID: {job_id}")
        print(f"Error: {e}")
        print("=" * 80)
        
        # Publish error
        publish_progress(job_id, {
            "type": "error",
            "content": str(e)
        })
        
        # Retry logic
        if self.request.retries < self.max_retries:
            print(f"⏳ Retrying... (attempt {self.request.retries + 1}/{self.max_retries})")
            raise self.retry(exc=e, countdown=10)
        
        # Max retries reached
        return {
            "job_id": job_id,
            "status": "failed",
            "error": str(e)
        }


# ============================================================================
# Health Check
# ============================================================================

@celery_app.task(name='tasks.health_check')
def health_check():
    """Simple health check task"""
    return {"status": "healthy", "worker": "llm"}