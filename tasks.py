# tasks.py - LLM Worker for EnhancedHTMLAppGenerator

from celery import Celery
import os
import asyncio
import json
import redis
from typing import Dict
from llm_worker import celery_app
from datetime import datetime, timezone 

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
        channel = f"job:{job_id}"
        redis_client.publish(channel, json.dumps(update))
    except Exception as e:
        print(f"[PROGRESS] Failed: {e}")

# ✅ Import YOUR class (EnhancedHTMLAppGenerator)
from deep_search import EnhancedHTMLAppGenerator

# ============================================================================
# Helper: Call Scraper and Wait
# ============================================================================

def call_scraper_and_wait(
    job_id: str,
    urls: list,
    search_query: str,
    original_query: str,
    timeout: int = 600
):
    """Send URLs to scraper worker and wait for results"""
    
    print("=" * 80)
    print("[SCRAPER_CALLBACK] STARTING SCRAPER DISPATCH")
    print("=" * 80)
    print(f"[SCRAPER_CALLBACK] Job ID: {job_id}")
    print(f"[SCRAPER_CALLBACK] Number of URLs: {len(urls)}")
    print(f"[SCRAPER_CALLBACK] Search Query: {search_query}")
    print(f"[SCRAPER_CALLBACK] Original Query: {original_query}")
    print(f"[SCRAPER_CALLBACK] URLs to scrape:")
    for i, url in enumerate(urls, 1):
        print(f"  {i}. {url}")
    print("=" * 80)
    
    try:
        # Dispatch task to scraper queue
        print("[SCRAPER_CALLBACK] Dispatching task to 'scraper_queue'...")
        
        scrape_task = celery_app.send_task(
            'tasks.scrape_content_task',
            args=[job_id, urls, search_query, original_query],
            queue='scraper_queue'
        )
        
        print(f"[SCRAPER_CALLBACK] ✅ Task dispatched successfully")
        print(f"[SCRAPER_CALLBACK] Task ID: {scrape_task.id}")
        print(f"[SCRAPER_CALLBACK] Task State: {scrape_task.state}")
        print(f"[SCRAPER_CALLBACK] Waiting for results (timeout: {timeout}s)...")
        
        # Wait for result
        result = scrape_task.get(timeout=timeout)
        
        print("=" * 80)
        print("[SCRAPER_CALLBACK] RECEIVED RESULT FROM SCRAPER")
        print("=" * 80)
        print(f"[SCRAPER_CALLBACK] Result Type: {type(result)}")
        print(f"[SCRAPER_CALLBACK] Result Keys: {result.keys() if isinstance(result, dict) else 'N/A'}")
        
        # Parse scraper return format
        if isinstance(result, dict) and 'data' in result:
            scraped_data = result['data'].get('results', [])
            print(f"[SCRAPER_CALLBACK] Format: dict with 'data' key")
        elif isinstance(result, dict) and 'results' in result:
            scraped_data = result['results']
            print(f"[SCRAPER_CALLBACK] Format: dict with 'results' key")
        elif isinstance(result, list):
            scraped_data = result
            print(f"[SCRAPER_CALLBACK] Format: direct list")
        else:
            scraped_data = []
            print(f"[SCRAPER_CALLBACK] ⚠️ Unknown format, returning empty list")
        
        print(f"[SCRAPER_CALLBACK] Returning {len(scraped_data)} results")
        print("=" * 80)
        
        return scraped_data
        
    except Exception as e:
        print("=" * 80)
        print("[SCRAPER_CALLBACK] ❌ ERROR OCCURRED")
        print("=" * 80)
        print(f"[SCRAPER_CALLBACK] Error Type: {type(e).__name__}")
        print(f"[SCRAPER_CALLBACK] Error Message: {e}")
        import traceback
        traceback.print_exc()
        print("=" * 80)
        return []
# ============================================================================
# Main Task: Deep Search (HTML App Generation)
# ============================================================================

# @celery_app.task(
#     bind=True,
#     result_extended=False ,
#     max_retries=1,
#     soft_time_limit=900,
#     time_limit=960,
#     name='tasks.deep_search_task'
# )
# def deep_search_task(self, job_id: str, query: str, conversation_history: list = None):
#     """
#     Main task for HTML app generation with research pipeline
#     """
    
#     print("=" * 80)
#     print("🚀 Starting deep_search_task (HTML App Generation)")
#     print("=" * 80)
#     print(f"Job ID: {job_id}")
#     print(f"Query: {query}")
#     print("=" * 80)
    
#     try:
#         publish_progress(job_id, {
#             "type": "reasoning",
#             "content": "Initializing HTML app generation..."
#         })
        
#         # ✅ Initialize YOUR generator
#         generator = EnhancedHTMLAppGenerator(
#             enable_reasoning_capture=True,
#             verbose=True,
#             max_search_queries=5,
#             max_urls_to_scrape=5,
#             scrape_timeout=600
#         )
        
#         # ✅ INJECT CALLBACKS
#         # generator.scraper_callback = lambda urls, sq, oq: asyncio.run(
#         #     call_scraper_and_wait(job_id, urls, sq, oq)
#         # )
        
#         generator.scraper_callback = lambda urls, sq, oq: call_scraper_and_wait(
#             job_id, urls, sq, oq
#         )
        
#         generator.progress_callback = lambda update: publish_progress(job_id, update)
        
#         print("✅ Generator initialized with callbacks")
        
#         # ✅ Run pipeline (using develop_app, NOT develop_report)
#         final_html = None  # ✅ Changed from final_markdown
#         analysis_summary = None
        
#         def run_pipeline():
#             nonlocal final_html, analysis_summary
            
#             # ✅ Call develop_app (NOT develop_report)
#             for result in generator.develop_app(
#                 user_prompt=query,
#                 conversation_history=conversation_history,
#                 use_multi_stage=True,
#                 enable_scraping=True,
#                 return_conversation=True
#             ):
#                 result_type = result.get("type")
                
#                 if result_type in ["reasoning", "sources"]:
#                     publish_progress(job_id, result)
                
#                 # ✅ Check for "html" not "markdown"
#                 elif result_type == "html":
#                     final_html = result.get("content")
#                     print(f"✅ HTML generated: {len(final_html)} characters")
                
#                 elif result_type == "analysis_summary":
#                     analysis_summary = result.get("content")
#                     print(f"✅ Analysis summary generated")
                
#                 elif result_type == "done":
#                     print(f"✅ Development complete")
        
#         # asyncio.run(run_pipeline())
#         run_pipeline()
        
#         # ✅ Check for HTML not markdown
#         if not final_html:
#             raise Exception("No HTML generated")
        
#         print("✅ HTML generated successfully")
        
#         # ✅ Return HTML not markdown
#         result_data = {
#             "job_id": job_id,
#             "status": "completed",
#             "html": final_html[1:10],  # ✅ Changed from "markdown"
#             "analysis_summary": analysis_summary or "Analysis not available",
#             "conversation_history": generator.get_conversation_history()
#         }
        
#         print("=" * 80)
#         print("✅ DEEP SEARCH TASK COMPLETED")
        
#         import random
#         random_num = random.randint(1, 100)
#         filename = f"output_{random_num}.html"
        
#         with open(filename, 'w', encoding='utf-8') as f:
#             f.write(final_html)
        
#         print(f"✅ Saved to {filename}")
        
#         print("=" * 80)
#         print(f"Job ID: {job_id}")
#         print(f"HTML length: {len(final_html)}")  # ✅ Changed from "Markdown length"
#         print(f"Analysis summary: {'Yes' if analysis_summary else 'No'}")
#         print("=" * 80)
        
#         publish_progress(job_id, {
#             "type": "complete",
#             "content": final_html  # ✅ Changed from final_markdown
#         })
        
#         # Update database if available
#         try:
#             from database import SessionLocal
#             from models import SearchJob, JobStatus
            
#             db = SessionLocal()
#             job = db.query(SearchJob).filter(SearchJob.id == job_id).first()
#             if job:
#                 job.status = JobStatus.COMPLETED
#                 job.result = json.dumps(result_data)
#                 db.commit()
#             db.close()
#         except Exception as e:
#             print(f"⚠️ Database update failed: {e}")
        
#         return result_data
        
#     except Exception as e:
#         print("=" * 80)
#         print("❌ DEEP SEARCH TASK FAILED")
#         print("=" * 80)
#         print(f"Job ID: {job_id}")
#         print(f"Error: {e}")
#         print("=" * 80)
        
#         import traceback
#         traceback.print_exc()
        
#         publish_progress(job_id, {
#             "type": "error",
#             "content": f"Error: {str(e)}"
#         })
        
#         if self.request.retries < self.max_retries:
#             print(f"⏳ Retrying...")
#             raise self.retry(exc=e, countdown=10)
        
#         # Update database on failure
#         try:
#             from database import SessionLocal
#             from models import SearchJob, JobStatus
            
#             db = SessionLocal()
#             job = db.query(SearchJob).filter(SearchJob.id == job_id).first()
#             if job:
#                 job.status = JobStatus.FAILED
#                 job.result = json.dumps({"error": str(e)})
#                 db.commit()
#             db.close()
#         except:
#             pass
        
#         raise


@celery_app.task(
    bind=True,
    result_extended=False,
    max_retries=1,
    soft_time_limit=900,
    time_limit=960,
    name='tasks.deep_search_task'
)
def deep_search_task(
    self, 
    job_id: str, 
    conversation_id: str,
    query: str, 
    conversation_history: list = None,
    file_contents: list = None,
    lab_mode: bool = False
):
    """
    Deep search or lab mode task - NO database writes, only Redis publishing
    """
    
    print("=" * 80)
    print("🚀 Starting deep_search_task")
    print("=" * 80)
    print(f"Job ID: {job_id}")
    print(f"Conversation ID: {conversation_id}")
    print(f"Query: {query}")
    print(f"Lab Mode: {lab_mode}")
    print(f"Files: {len(file_contents) if file_contents else 0}")
    print("=" * 80)
   
    try:
        # Choose generator based on mode        
        print("[TASK] Initializing EnhancedHTMLAppGenerator...")
        from deep_search import EnhancedHTMLAppGenerator
        generator = EnhancedHTMLAppGenerator(
            verbose=True,
            max_search_queries=5,
            max_urls_to_scrape=5,
            scrape_timeout=600
        )
        generator.conversation_history = conversation_history
        
        generator_method = generator.develop_app
        
        # ✅ INJECT SCRAPER CALLBACK
        print("[TASK] Injecting scraper callback...")
        generator.scraper_callback = lambda urls, sq, oq: call_scraper_and_wait(
            job_id, urls, sq, oq
        )
        print("[TASK] ✅ Scraper callback injected")
        
        # ✅ INJECT PROGRESS CALLBACK
        print("[TASK] Injecting progress callback...")
        generator.progress_callback = lambda update: publish_progress(job_id, update)
        print("[TASK] ✅ Progress callback injected")
         
        
        # Prepare query with file contents if present
        full_query = query
        if file_contents:
            full_query += "\n\n=== UPLOADED FILES ===\n"
            for file_info in file_contents:
                full_query += f"\n--- {file_info['filename']} ({file_info['type']}) ---\n"
                full_query += file_info['content']
                full_query += "\n" + "="*50 + "\n"
        
        # Track final results
        final_content = ""
        final_sources = []
        final_reasoning_steps = []
        final_assets = []
        final_app = None
        
        print("[TASK] Starting generation pipeline...")
        print("=" * 80)
        
        # Run generator and publish progress
        def run_generation():
            nonlocal final_content, final_sources, final_reasoning_steps, final_assets, final_app
            
            for result in generator_method(full_query, conversation_history or [],lab_mode):
                result_type = result.get("type")
                
                # Publish reasoning/sources to Redis (for client streaming)
                if result_type == "reasoning":
                    publish_progress(job_id, {
                        "type": "reasoning",
                        "step": result.get("content"),
                        "content": result.get("content"),
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
                
                elif result_type == "sources":
                    content = result.get("content")
                    urls = content.get("urls", [])
                    transformed_query = content.get("transformed_query", "")
                    
                    final_sources.append(urls)
                    
                    publish_progress(job_id, {
                        "type": "reasoning",
                        "step": "Sources Found",
                        "content": transformed_query,
                        "found_sources": len(urls),
                        "sources": urls,
                        "query": transformed_query,
                        "category": "Web Search",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
                
                # Collect final outputs (don't publish yet)
                elif result_type == "html":
                    final_app = result.get("content")
                    print(f"✅ HTML generated: {len(final_app)} chars")
                
                elif result_type == "markdown":
                    final_app = result.get("content")
                    print(f"✅ Markdown generated: {len(final_app)} chars")
                
                elif result_type == "analysis_summary":
                    final_content = result.get("content")
                    print(f"✅ Analysis summary: {len(final_content)} chars")
                
                elif result_type == "done":
                    print("✅ Generation complete")
        
        # Run the generator
        run_generation()
        
        # Publish final structured result
        final_result = {
            "type": "complete",
            "conversation_id": conversation_id,
            "content": final_content,
            "sources": final_sources,
            "reasoning_steps": final_reasoning_steps,
            "assets": final_assets,
            "app": final_app,
            "lab_mode": lab_mode
        }
        
        publish_progress(job_id, final_result)
        
        print("=" * 80)
        print("✅ TASK COMPLETED SUCCESSFULLY")
        print("=" * 80)
        
        return final_result
        
    except Exception as e:
        print("=" * 80)
        print("❌ TASK FAILED")
        print("=" * 80)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        
        # Publish error
        publish_progress(job_id, {
            "type": "error",
            "conversation_id": conversation_id,
            "message": f"We encountered an issue processing your request. Please try again.",
            "fatal": True
        })
        
        raise
    
@celery_app.task(name='tasks.health_check')
def health_check():
    print("running")
    """Health check task"""
    return {
        "status": "healthy",
        "worker": "llm_worker_html"
    }