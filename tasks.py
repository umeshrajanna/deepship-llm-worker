# tasks.py - LLM Worker (Updated for deep_search.py with callbacks)

from celery import Celery
import os
import asyncio
import json
import redis
from typing import Dict

# Celery app configuration
celery_app = Celery(
    'llm_worker',
    broker=os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
    backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_routes={
        'tasks.deep_search_task': {'queue': 'llm'},
        'tasks.scrape_content_task': {'queue': 'scraper_queue'},
    },
    task_track_started=True,
    result_expires=3600,
)

# ============================================================================
# Redis Client for Progress Updates
# ============================================================================

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

try:
    redis_client = redis.from_url(
        redis_url,
        decode_responses=True,
        socket_connect_timeout=5,
        retry_on_timeout=True
    )
    redis_client.ping()
    print(f"[REDIS] ✅ Connected to {redis_url}")
except Exception as e:
    print(f"[REDIS] ⚠️ Connection failed: {e}")
    redis_client = None

def publish_progress(job_id: str, update: Dict):
    """Publish progress update to Redis pub/sub channel"""
    if not redis_client:
        print(f"[PROGRESS] Skipped (Redis unavailable): {update.get('type')}")
        return
    
    try:
        channel = f"job:{job_id}:progress"
        redis_client.publish(channel, json.dumps(update))
        print(f"[PROGRESS] Published: {update.get('type')}")
    except Exception as e:
        print(f"[PROGRESS] Failed (non-fatal): {e}")

# ============================================================================
# Import Deep Search Generator
# ============================================================================

from deep_search import EnhancedHTMLAppGenerator

# ============================================================================
# Helper: Call Scraper and Wait
# ============================================================================

async def call_scraper_and_wait(
    job_id: str,
    urls: list,
    search_query: str,
    original_query: str,
    timeout: int = 600
):
    """
    Send URLs to scraper worker and wait for results
    
    This function:
    1. Dispatches task to scraper_queue
    2. Waits for scraper to complete
    3. Parses and returns scraped results
    """
    
    print(f"✅ [SCRAPER_CALLBACK] Dispatching scraper task for {len(urls)} URLs")
    
    # Dispatch to scraper queue
    scrape_task = celery_app.send_task(
        'tasks.scrape_content_task',
        args=[job_id, urls, search_query, original_query],
        queue='scraper_queue'
    )
    
    print(f"✅ [SCRAPER_CALLBACK] Task ID: {scrape_task.id}")
    
    # Wait for results
    try:
        result = scrape_task.get(timeout=timeout)
        print(f"✅ [SCRAPER_CALLBACK] Received result: {type(result)}")
        
        # Parse scraper's return format
        # Scraper might return:
        # - {"data": {"results": [...]}}
        # - {"results": [...]}
        # - [...]
        
        if isinstance(result, dict) and 'data' in result:
            scraped_data = result['data'].get('results', [])
        elif isinstance(result, dict) and 'results' in result:
            scraped_data = result['results']
        elif isinstance(result, list):
            scraped_data = result
        else:
            print(f"⚠️ [SCRAPER_CALLBACK] Unexpected format: {type(result)}")
            scraped_data = []
        
        print(f"✅ [SCRAPER_CALLBACK] Returning {len(scraped_data)} results")
        return scraped_data
        
    except Exception as e:
        print(f"❌ [SCRAPER_CALLBACK] Error: {e}")
        import traceback
        traceback.print_exc()
        return []

# ============================================================================
# Main Task: Deep Search
# ============================================================================

@celery_app.task(
    bind=True,
    max_retries=1,
    soft_time_limit=900,  # 15 minutes
    time_limit=960,       # 16 minutes
    name='tasks.deep_search_task'
)
def deep_search_task(self, job_id: str, query: str, conversation_history: list = None):
    """
    Main orchestration task for deep search with markdown generation
    
    Args:
        job_id: Unique job identifier
        query: User's search query
        conversation_history: Previous conversation context (optional)
    
    Returns:
        Dict with markdown, analysis_summary, and conversation_history
    """
    
    print("=" * 80)
    print("🚀 Starting deep_search_task")
    print("=" * 80)
    print(f"Job ID: {job_id}")
    print(f"Query: {query}")
    print(f"Has conversation history: {conversation_history is not None}")
    print("=" * 80)
    
    try:
        # Publish initial progress
        publish_progress(job_id, {
            "type": "reasoning",
            "content": "Initializing deep search..."
        })
        
        # ====================================================================
        # Initialize Generator
        # ====================================================================
        generator = EnhancedHTMLAppGenerator(
            enable_reasoning_capture=True,
            verbose=True,
            max_search_queries=5,
            max_urls_to_scrape=5,
            scrape_timeout=600
        )
        
        # ====================================================================
        # ✅ INJECT SCRAPER CALLBACK
        # ====================================================================
        # This callback will be called by deep_search.py when it needs to scrape URLs
        generator.scraper_callback = lambda urls, sq, oq: asyncio.run(
            call_scraper_and_wait(job_id, urls, sq, oq)
        )
        
        # ====================================================================
        # ✅ INJECT PROGRESS CALLBACK
        # ====================================================================
        # This callback will be called for progress updates
        generator.progress_callback = lambda update: publish_progress(job_id, update)
        
        print("✅ Generator initialized with callbacks")
        print(f"   - Scraper callback: {generator.scraper_callback is not None}")
        print(f"   - Progress callback: {generator.progress_callback is not None}")
        
        # ====================================================================
        # Run the Full Pipeline
        # ====================================================================
        print("🚀 Starting develop_report...")
        
        final_markdown = None
        analysis_summary = None
        
        async def run_pipeline():
            nonlocal final_markdown, analysis_summary
            
            async for result in generator.develop_report(
                user_prompt=query,
                conversation_history=conversation_history,
                use_multi_stage=True,
                enable_scraping=True,
                return_conversation=True
            ):
                # Forward progress updates to Redis
                result_type = result.get("type")
                
                if result_type in ["reasoning", "sources"]:
                    publish_progress(job_id, result)
                    print(f"[PROGRESS] {result_type}: {str(result.get('content'))[:100]}")
                
                elif result_type == "markdown":
                    final_markdown = result.get("content")
                    print(f"✅ Markdown generated: {len(final_markdown)} characters")
                
                elif result_type == "analysis_summary":
                    analysis_summary = result.get("content")
                    print(f"✅ Analysis summary generated")
                
                elif result_type == "done":
                    print(f"✅ Development complete")
        
        # Execute the async pipeline
        asyncio.run(run_pipeline())
        
        if not final_markdown:
            raise Exception("No markdown generated")
        
        print("✅ Markdown generated successfully")
        print("✅ Analysis summary generated" if analysis_summary else "⚠️ No analysis summary")
        
        # ====================================================================
        # Prepare Result
        # ====================================================================
        result_data = {
            "job_id": job_id,
            "status": "completed",
            "markdown": final_markdown,
            "analysis_summary": analysis_summary or "Analysis not available",
            "conversation_history": generator.get_conversation_history()
        }
        
        print("=" * 80)
        print("✅ DEEP SEARCH TASK COMPLETED")
        print("=" * 80)
        print(f"Job ID: {job_id}")
        print(f"Markdown length: {len(final_markdown)}")
        print(f"Analysis summary: {'Yes' if analysis_summary else 'No'}")
        print("=" * 80)
        
        # Publish completion
        publish_progress(job_id, {
            "type": "complete",
            "content": final_markdown
        })
        
        # Update database if available
        try:
            from database import SessionLocal
            from models import SearchJob, JobStatus
            
            db = SessionLocal()
            job = db.query(SearchJob).filter(SearchJob.id == job_id).first()
            if job:
                job.status = JobStatus.COMPLETED
                job.result = json.dumps(result_data)
                db.commit()
            db.close()
            print("✅ Database updated")
        except Exception as e:
            print(f"⚠️ Failed to update database: {e}")
        
        return result_data
        
    except Exception as e:
        print("=" * 80)
        print("❌ DEEP SEARCH TASK FAILED")
        print("=" * 80)
        print(f"Job ID: {job_id}")
        print(f"Error: {e}")
        print("=" * 80)
        
        import traceback
        traceback.print_exc()
        
        # Publish error
        publish_progress(job_id, {
            "type": "error",
            "content": f"Search failed: {str(e)}"
        })
        
        # Retry if possible
        if self.request.retries < self.max_retries:
            retry_delay = 10
            print(f"⏳ Retrying... (attempt {self.request.retries + 1}/{self.max_retries})")
            publish_progress(job_id, {
                "type": "reasoning",
                "content": f"Retrying in {retry_delay}s..."
            })
            raise self.retry(exc=e, countdown=retry_delay)
        
        # Max retries reached - update database
        try:
            from database import SessionLocal
            from models import SearchJob, JobStatus
            
            db = SessionLocal()
            job = db.query(SearchJob).filter(SearchJob.id == job_id).first()
            if job:
                job.status = JobStatus.FAILED
                job.result = json.dumps({"error": str(e)})
                db.commit()
            db.close()
        except:
            pass
        
        raise

# ============================================================================
# Health Check
# ============================================================================

@celery_app.task(name='tasks.health_check')
def health_check():
    """Simple health check task"""
    return {
        "status": "healthy",
        "worker": "llm_worker",
        "has_deep_search": True
    }