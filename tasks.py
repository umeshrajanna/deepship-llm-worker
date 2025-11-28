# tasks.py - LLM Worker (No Scraper Dependencies)
# Handles query analysis and synthesis, dispatches to scraper worker

from celery import Celery
from celery.result import AsyncResult
import os
import time
import json
from typing import List, Dict, Any

# Celery app configuration
celery_app = Celery(
    'deepship',
    broker=os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379'),
    backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379')
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_routes={
        'tasks.deep_search_task': {'queue': 'celery'},
        'tasks.scrape_content_task': {'queue': 'scraper_queue'},
    },
    task_track_started=True,
    result_expires=3600,
)

# Import database and Redis utilities (lightweight)
try:
    from database import SessionLocal
    from models import SearchJob, JobStatus
    from redis_client import publish_progress
except ImportError:
    # Fallback if using flat structure
    pass

# ============================================================================
# Mock LLM Functions (Replace with Claude API)
# ============================================================================

def analyze_query_with_llm(query: str) -> Dict:
    """
    Mock: Analyze query and generate search angles
    TODO: Replace with actual Claude API call
    """
    print(f"🤖 [MOCK] Analyzing query: {query}")
    time.sleep(2)  # Simulate API call
    
    return {
        "search_angles": [
            {"angle": "recent developments", "search_query": f"{query} recent news 2024"},
            {"angle": "expert analysis", "search_query": f"{query} expert analysis"},
            {"angle": "statistical data", "search_query": f"{query} statistics data"},
        ]
    }

def synthesize_with_llm(query: str, scraped_content: List[Dict]) -> Dict:
    """
    Mock: Synthesize information from scraped content
    TODO: Replace with actual Claude API call
    """
    print(f"🤖 [MOCK] Synthesizing information for: {query}")
    time.sleep(2)  # Simulate API call
    
    total_sources = sum(
        len(item.get('data', {}).get('results', [])) 
        for item in scraped_content if item
    )
    
    return {
        "key_findings": [
            "Finding 1 based on multiple sources",
            "Finding 2 with supporting evidence",
            "Finding 3 from expert analysis"
        ],
        "source_count": total_sources,
        "confidence": "high"
    }

def format_answer_with_llm(query: str, synthesis: Dict) -> str:
    """
    Mock: Format final answer
    TODO: Replace with actual Claude API call
    """
    print(f"🤖 [MOCK] Formatting answer for: {query}")
    time.sleep(1)  # Simulate API call
    
    findings = synthesis.get('key_findings', [])
    source_count = synthesis.get('source_count', 0)
    
    answer = f"# Answer to: {query}\n\n"
    answer += f"Based on {source_count} sources:\n\n"
    
    for i, finding in enumerate(findings, 1):
        answer += f"{i}. {finding}\n"
    
    return answer

# ============================================================================
# Main Task: Deep Search (LLM Worker)
# ============================================================================

@celery_app.task(bind=True, max_retries=3, name='tasks.deep_search_task')
def deep_search_task(self, job_id: str, query: str):
    """
    Main orchestration task - runs on LLM worker
    
    1. Analyzes query with LLM
    2. Dispatches scraper tasks to scraper_queue
    3. Waits for scraping results
    4. Synthesizes findings with LLM
    5. Formats final answer
    
    NO SCRAPER IMPORTS - delegates scraping to scraper worker!
    """
    print(f"🚀 Starting deep_search_task for job {job_id}: {query}")
    
    try:
        # Update job status
        publish_progress(job_id, "reasoning", "Analyzing your query with AI...")
        
        # Step 1: Analyze query with LLM
        print(f"📊 Step 1: Analyzing query...")
        query_analysis = analyze_query_with_llm(query)
        
        publish_progress(
            job_id, 
            "reasoning", 
            f"Identified {len(query_analysis['search_angles'])} search angles"
        )
        
        # Step 2: Dispatch scraper tasks to scraper_queue
        print(f"🔍 Step 2: Dispatching {len(query_analysis['search_angles'])} scraper tasks...")
        
        scraper_tasks = []
        for angle in query_analysis['search_angles']:
            # Import scrape task signature (just for dispatching)
            from tasks_api import scrape_content_task
            
            task = scrape_content_task.apply_async(
                args=[job_id, angle['search_query'], query],
                queue='scraper_queue',  # Send to scraper worker!
                routing_key='scraper_queue'
            )
            scraper_tasks.append(task)
            print(f"   📤 Dispatched scraper task: {task.id} for '{angle['angle']}'")
        
        publish_progress(
            job_id,
            "content",
            f"Searching {len(scraper_tasks)} sources..."
        )
        
        # Step 3: Wait for scraper results (with timeout)
        print(f"⏳ Step 3: Waiting for scraper results...")
        all_scraped_content = []
        
        for i, task_result in enumerate(scraper_tasks, 1):
            try:
                # Wait for this scraper task to complete
                result = task_result.get(timeout=120)  # 2 min timeout per task
                all_scraped_content.append(result)
                
                publish_progress(
                    job_id,
                    "content",
                    f"Gathered information from source {i}/{len(scraper_tasks)}"
                )
                print(f"   ✅ Received result from scraper task {i}/{len(scraper_tasks)}")
                
            except Exception as e:
                print(f"   ⚠️ Scraper task {i} failed: {e}")
                publish_progress(
                    job_id,
                    "reasoning",
                    f"One source unavailable, continuing with others..."
                )
                continue
        
        if not all_scraped_content:
            raise Exception("No content could be scraped from any source")
        
        # Step 4: Synthesize findings with LLM
        print(f"🧠 Step 4: Synthesizing information...")
        publish_progress(job_id, "reasoning", "Synthesizing information from all sources...")
        
        synthesis = synthesize_with_llm(query, all_scraped_content)
        
        publish_progress(
            job_id,
            "content",
            f"Generated comprehensive answer with {synthesis.get('source_count', 0)} sources"
        )
        
        # Step 5: Format final answer with LLM
        print(f"✍️ Step 5: Formatting final answer...")
        publish_progress(job_id, "reasoning", "Formatting your answer...")
        
        final_answer = format_answer_with_llm(query, synthesis)
        
        # Step 6: Complete!
        print(f"✅ Deep search complete for job {job_id}")
        
        result_data = {
            "query": query,
            "answer": final_answer,
            "sources": all_scraped_content,
            "synthesis": synthesis,
            "status": "complete"
        }
        
        publish_progress(
            job_id,
            "complete",
            final_answer,
            full_result=result_data
        )
        
        # Update database
        try:
            db = SessionLocal()
            job = db.query(SearchJob).filter(SearchJob.id == job_id).first()
            if job:
                job.status = JobStatus.COMPLETED
                job.result = json.dumps(result_data)
                db.commit()
            db.close()
        except Exception as e:
            print(f"⚠️ Failed to update database: {e}")
        
        return result_data
        
    except Exception as e:
        print(f"❌ Error in deep_search_task: {e}")
        
        # Retry with exponential backoff
        if self.request.retries < self.max_retries:
            retry_delay = 10 * (2 ** self.request.retries)  # 10s, 20s, 40s
            publish_progress(
                job_id,
                "reasoning",
                f"Encountered an issue, retrying in {retry_delay}s..."
            )
            raise self.retry(exc=e, countdown=retry_delay)
        
        # Max retries reached - mark as failed
        publish_progress(
            job_id,
            "error",
            f"Search failed after multiple attempts: {str(e)}"
        )
        
        try:
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
    return {"status": "healthy", "worker": "llm"}