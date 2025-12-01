# stress_test_50_prompts.py
import redis
import os
from dotenv import load_dotenv
from tasks import deep_search_task
import time
from datetime import datetime

load_dotenv()

r = redis.from_url(os.getenv('CELERY_BROKER_URL'))

# 50 diverse prompts for stress testing
PROMPTS = [
    # Tech & AI (10 prompts)
    "Latest AI model releases and capabilities in 2024-2025",
    "Top AI startups by funding in 2024",
    "OpenAI GPT-5 rumors and release timeline",
    "Google Gemini vs Claude vs GPT-4 comparison",
    "AI regulation updates in EU and US",
    "NVIDIA stock performance and AI chip demand",
    "Tesla Optimus robot development progress",
    "Quantum computing breakthroughs 2024-2025",
    "Apple Vision Pro sales and adoption rates",
    "Microsoft Copilot features and pricing",
    
    # Climate & Environment (5 prompts)
    "Recent extreme weather events last 30 days",
    "Global temperature records broken in 2024",
    "Arctic ice melt statistics 2024-2025",
    "Renewable energy adoption by country",
    "Carbon capture technology advances",
    
    # Finance & Crypto (10 prompts)
    "Bitcoin price prediction 2025",
    "Ethereum ETF approval status",
    "Top performing stocks in 2024",
    "Federal Reserve interest rate forecast",
    "US inflation rate trends 2024-2025",
    "Gold vs Bitcoin as inflation hedge",
    "Real estate market predictions 2025",
    "Venture capital funding trends AI sector",
    "S&P 500 outlook for 2025",
    "GameStop stock latest news",
    
    # Sports (5 prompts)
    "Premier League standings and top scorers",
    "NBA championship favorites 2024-2025",
    "Cristiano Ronaldo latest transfer news",
    "Super Bowl 2025 predictions",
    "Olympics 2024 medal count by country",
    
    # Health & Medicine (5 prompts)
    "New drug approvals FDA 2024-2025",
    "COVID-19 variant tracking latest",
    "Ozempic weight loss effectiveness studies",
    "Cancer treatment breakthroughs 2024",
    "Life expectancy trends by country",
    
    # Business & Startups (5 prompts)
    "Unicorn startups 2024 list",
    "SpaceX Starship launch schedule",
    "Amazon Prime membership cost changes",
    "Tesla Cybertruck production numbers",
    "Disney+ subscriber count vs Netflix",
    
    # Politics & World Events (5 prompts)
    "US election 2024 polling data",
    "Ukraine war latest developments",
    "China Taiwan relations current status",
    "Middle East conflict updates",
    "UK immigration policy changes 2024",
    
    # Entertainment (5 prompts)
    "Top grossing movies 2024",
    "Netflix original series ratings",
    "Taylor Swift Eras Tour revenue",
    "Oscar nominations 2025 predictions",
    "PlayStation 6 release date rumors"
]

def run_stress_test():
    """Run stress test with 50 prompts"""
    
    print("=" * 100)
    print("🔥 STRESS TEST: 50 CONCURRENT PROMPTS")
    print("=" * 100)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total prompts: {len(PROMPTS)}")
    print(f"Worker queues: llm_queue, scraper_queue")
    print("=" * 100)
    print()
    
    results = []
    start_time = time.time()
    
    # Submit all tasks
    print("📤 SUBMITTING TASKS...")
    print("-" * 100)
    
    for i, prompt in enumerate(PROMPTS, 1):
        job_id = f"stress-test-{i:03d}"
        
        print(f"[{i:02d}/{len(PROMPTS)}] Submitting: {prompt[:60]}...")
        
        try:
            result = deep_search_task.delay(job_id, prompt, [])
            
            results.append({
                'job_id': job_id,
                'prompt': prompt,
                'task_id': result.id,
                'result_obj': result,
                'submitted_at': time.time()
            })
            
            print(f"          ✅ Task ID: {result.id}")
            
        except Exception as e:
            print(f"          ❌ Error: {e}")
            results.append({
                'job_id': job_id,
                'prompt': prompt,
                'task_id': None,
                'result_obj': None,
                'submitted_at': time.time(),
                'error': str(e)
            })
    
    submission_time = time.time() - start_time
    
    print()
    print("-" * 100)
    print(f"✅ All tasks submitted in {submission_time:.2f}s")
    print("=" * 100)
    print()
    
    # Monitor progress
    print("📊 MONITORING PROGRESS...")
    print("-" * 100)
    
    monitoring_start = time.time()
    completed = 0
    failed = 0
    pending = len([r for r in results if r.get('result_obj')])
    
    print(f"\n{'Time':<12} {'Completed':<12} {'Failed':<12} {'Pending':<12} {'Total':<12}")
    print("-" * 100)
    
    last_update = 0
    
    while pending > 0:
        time.sleep(2)  # Check every 2 seconds
        
        completed = 0
        failed = 0
        pending = 0
        
        for r in results:
            if not r.get('result_obj'):
                failed += 1
                continue
            
            task = r['result_obj']
            state = task.state
            
            if state == 'SUCCESS':
                completed += 1
            elif state in ['FAILURE', 'REVOKED']:
                failed += 1
            else:
                pending += 1
        
        elapsed = time.time() - monitoring_start
        
        # Update every 10 seconds
        if elapsed - last_update >= 10:
            print(f"{elapsed:<12.1f} {completed:<12} {failed:<12} {pending:<12} {len(results):<12}")
            last_update = elapsed
        
        # Timeout after 30 minutes
        if elapsed > 1800:
            print("\n⏱️ Timeout reached (30 minutes)")
            break
    
    total_time = time.time() - start_time
    
    print()
    print("=" * 100)
    print("🎉 STRESS TEST COMPLETE")
    print("=" * 100)
    
    # Final statistics
    final_completed = 0
    final_failed = 0
    final_pending = 0
    
    for r in results:
        if not r.get('result_obj'):
            final_failed += 1
            continue
        
        task = r['result_obj']
        state = task.state
        
        if state == 'SUCCESS':
            final_completed += 1
        elif state in ['FAILURE', 'REVOKED']:
            final_failed += 1
        else:
            final_pending += 1
    
    print(f"\n📊 FINAL STATISTICS:")
    print(f"   Total tasks: {len(results)}")
    print(f"   Completed: {final_completed} ({final_completed/len(results)*100:.1f}%)")
    print(f"   Failed: {final_failed} ({final_failed/len(results)*100:.1f}%)")
    print(f"   Still pending: {final_pending} ({final_pending/len(results)*100:.1f}%)")
    print(f"\n⏱️ TIMING:")
    print(f"   Submission time: {submission_time:.2f}s")
    print(f"   Total time: {total_time:.2f}s")
    print(f"   Average per task: {total_time/len(results):.2f}s")
    
    # Show sample results
    print(f"\n📋 SAMPLE RESULTS (first 5 completed):")
    print("-" * 100)
    
    shown = 0
    for r in results:
        if shown >= 5:
            break
        
        if r.get('result_obj') and r['result_obj'].state == 'SUCCESS':
            print(f"\n✅ {r['job_id']}")
            print(f"   Prompt: {r['prompt'][:80]}...")
            print(f"   Task ID: {r['task_id']}")
            
            try:
                result_data = r['result_obj'].result
                print(f"   Status: {result_data.get('status', 'unknown')}")
                
                if 'html_length' in result_data:
                    print(f"   HTML length: {result_data['html_length']:,} chars")
                
                if 'saved_to_file' in result_data:
                    print(f"   Saved to: {result_data['saved_to_file']}")
            except Exception as e:
                print(f"   Error retrieving result: {e}")
            
            shown += 1
    
    # Show failures
    failures = [r for r in results if not r.get('result_obj') or r['result_obj'].state in ['FAILURE', 'REVOKED']]
    
    if failures:
        print(f"\n❌ FAILURES ({len(failures)} total):")
        print("-" * 100)
        
        for r in failures[:5]:  # Show first 5 failures
            print(f"\n❌ {r['job_id']}")
            print(f"   Prompt: {r['prompt'][:80]}...")
            
            if r.get('error'):
                print(f"   Error: {r['error']}")
            elif r.get('result_obj'):
                try:
                    print(f"   State: {r['result_obj'].state}")
                    print(f"   Info: {r['result_obj'].info}")
                except:
                    pass
    
    print("\n" + "=" * 100)
    print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 100)
    
    return results


if __name__ == "__main__":
    try:
        results = run_stress_test()
        
        # Save results to file
        import json
        
        results_file = f"stress_test_results_{int(time.time())}.json"
        
        serializable_results = []
        for r in results:
            result_dict = {
                'job_id': r['job_id'],
                'prompt': r['prompt'],
                'task_id': r.get('task_id'),
                'submitted_at': r['submitted_at']
            }
            
            if r.get('result_obj'):
                result_dict['state'] = r['result_obj'].state
                
                try:
                    if r['result_obj'].state == 'SUCCESS':
                        result_dict['result'] = r['result_obj'].result
                except:
                    pass
            
            if r.get('error'):
                result_dict['error'] = r['error']
            
            serializable_results.append(result_dict)
        
        with open(results_file, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'total_prompts': len(PROMPTS),
                'results': serializable_results
            }, f, indent=2)
        
        print(f"\n💾 Results saved to: {results_file}")
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()