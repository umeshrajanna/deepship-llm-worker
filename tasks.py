# tasks.py - LLM Worker for EnhancedHTMLAppGenerator

from celery import Celery
import os
import asyncio
import json
import redis
from typing import Dict
from llm_worker import celery_app

# Celery app configuration
# celery_app = Celery(
#     'llm_worker',
#     broker=os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
#     backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
# )

# celery_app.conf.update(
#     task_serializer='json',
#     accept_content=['json'],
#     result_serializer='json',
#     timezone='UTC',
#     enable_utc=True,
#     task_routes={
#         'tasks.deep_search_task': {'queue': 'llm'},
#         'tasks.scrape_content_task': {'queue': 'scraper_queue'},
#     },
#     task_track_started=True,
#     result_expires=3600,
# )

# Redis client for progress updates
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

try:
    redis_client = redis.from_url(
        redis_url,
        decode_responses=True,
        socket_connect_timeout=5,
        retry_on_timeout=True
    )
    redis_client.ping()
    print(f"[REDIS] ✅ Connected")
except Exception as e:
    print(f"[REDIS] ⚠️ Failed: {e}")
    redis_client = None

def publish_progress(job_id: str, update: Dict):
    """Publish progress update to Redis pub/sub channel"""
    if not redis_client:
        return
    
    try:
        channel = f"job:{job_id}:progress"
        redis_client.publish(channel, json.dumps(update))
    except Exception as e:
        print(f"[PROGRESS] Failed: {e}")

# ✅ Import YOUR class (EnhancedHTMLAppGenerator)
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
    """Send URLs to scraper worker and wait for results"""
    
    print(f"[SCRAPER_CALLBACK] Dispatching scraper for {len(urls)} URLs")
    
    scrape_task = celery_app.send_task(
        'tasks.scrape_content_task',
        args=[job_id, urls, search_query, original_query],
        queue='scraper_queue'
    )
    
    print(f"[SCRAPER_CALLBACK] Task ID: {scrape_task.id}")
    
    try:
        result = scrape_task.get(timeout=timeout)
        print(f"[SCRAPER_CALLBACK] Received: {type(result)}")
        
        # Parse scraper return format
        if isinstance(result, dict) and 'data' in result:
            scraped_data = result['data'].get('results', [])
        elif isinstance(result, dict) and 'results' in result:
            scraped_data = result['results']
        elif isinstance(result, list):
            scraped_data = result
        else:
            scraped_data = []
        
        print(f"[SCRAPER_CALLBACK] Returning {len(scraped_data)} results")
        return scraped_data
        
    except Exception as e:
        print(f"[SCRAPER_CALLBACK] Error: {e}")
        return []

# ============================================================================
# Main Task: Deep Search (HTML App Generation)
# ============================================================================

@celery_app.task(
    bind=True,
    max_retries=1,
    soft_time_limit=900,
    time_limit=960,
    name='tasks.deep_search_task'
)
def deep_search_task(self, job_id: str, query: str, conversation_history: list = None):
    """
    Main task for HTML app generation with research pipeline
    """
    
    print("=" * 80)
    print("🚀 Starting deep_search_task (HTML App Generation)")
    print("=" * 80)
    print(f"Job ID: {job_id}")
    print(f"Query: {query}")
    print("=" * 80)
    
    try:
        publish_progress(job_id, {
            "type": "reasoning",
            "content": "Initializing HTML app generation..."
        })
        
        # ✅ Initialize YOUR generator
        generator = EnhancedHTMLAppGenerator(
            enable_reasoning_capture=True,
            verbose=True,
            max_search_queries=5,
            max_urls_to_scrape=5,
            scrape_timeout=600
        )
        
        # ✅ INJECT CALLBACKS
        generator.scraper_callback = lambda urls, sq, oq: asyncio.run(
            call_scraper_and_wait(job_id, urls, sq, oq)
        )
        generator.progress_callback = lambda update: publish_progress(job_id, update)
        
        print("✅ Generator initialized with callbacks")
        
        # ✅ Run pipeline (using develop_app, NOT develop_report)
        final_html = None  # ✅ Changed from final_markdown
        analysis_summary = None
        
        async def run_pipeline():
            nonlocal final_html, analysis_summary
            
            # ✅ Call develop_app (NOT develop_report)
            async for result in generator.develop_app(
                user_prompt=query,
                conversation_history=conversation_history,
                use_multi_stage=True,
                enable_scraping=True,
                return_conversation=True
            ):
                result_type = result.get("type")
                
                if result_type in ["reasoning", "sources"]:
                    publish_progress(job_id, result)
                
                # ✅ Check for "html" not "markdown"
                elif result_type == "html":
                    final_html = result.get("content")
                    print(f"✅ HTML generated: {len(final_html)} characters")
                
                elif result_type == "analysis_summary":
                    analysis_summary = result.get("content")
                    print(f"✅ Analysis summary generated")
                
                elif result_type == "done":
                    print(f"✅ Development complete")
        
        asyncio.run(run_pipeline())
        
        # ✅ Check for HTML not markdown
        if not final_html:
            raise Exception("No HTML generated")
        
        print("✅ HTML generated successfully")
        
        # ✅ Return HTML not markdown
        result_data = {
            "job_id": job_id,
            "status": "completed",
            "html": final_html,  # ✅ Changed from "markdown"
            "analysis_summary": analysis_summary or "Analysis not available",
            "conversation_history": generator.get_conversation_history()
        }
        
        print("=" * 80)
        print("✅ DEEP SEARCH TASK COMPLETED")
        print("=" * 80)
        print(f"Job ID: {job_id}")
        print(f"HTML length: {len(final_html)}")  # ✅ Changed from "Markdown length"
        print(f"Analysis summary: {'Yes' if analysis_summary else 'No'}")
        print("=" * 80)
        
        publish_progress(job_id, {
            "type": "complete",
            "content": final_html  # ✅ Changed from final_markdown
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
        except Exception as e:
            print(f"⚠️ Database update failed: {e}")
        
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
        
        publish_progress(job_id, {
            "type": "error",
            "content": f"Error: {str(e)}"
        })
        
        if self.request.retries < self.max_retries:
            print(f"⏳ Retrying...")
            raise self.retry(exc=e, countdown=10)
        
        # Update database on failure
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

@celery_app.task(name='tasks.health_check')
def health_check():
    print("running")
    """Health check task"""
    return {
        "status": "healthy",
        "worker": "llm_worker_html"
    }