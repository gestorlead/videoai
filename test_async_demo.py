#!/usr/bin/env python3
"""
VideoAI Async Processing Demo - Complete End-to-End Test
Demonstrates job submission, real-time monitoring, and result retrieval
"""

import asyncio
import time
import requests
import json
from app.core.celery import celery_app
from app.tasks.ai_tasks import generate_image_with_ai


def test_celery_direct():
    """Test 1: Direct Celery task execution"""
    print("🧪 Test 1: Direct Celery Task Execution")
    print("=" * 50)
    
    # Submit task directly to Celery
    task = generate_image_with_ai.delay(
        prompt="A futuristic robot creating digital art",
        model="dall-e-3"
    )
    
    print(f"✅ Task submitted! Job ID: {task.id}")
    print(f"📍 Task name: {task.name}")
    print(f"🔄 Initial status: {task.status}")
    
    # Monitor task progress
    print("\n📊 Monitoring task progress...")
    start_time = time.time()
    
    while not task.ready():
        current_state = task.state
        if current_state == 'PROGRESS':
            progress_info = task.info
            progress = progress_info.get('progress', 0)
            status_msg = progress_info.get('status', 'Processing...')
            
            # Progress bar
            bar_length = 30
            filled_length = int(bar_length * progress // 100)
            bar = '█' * filled_length + '-' * (bar_length - filled_length)
            
            print(f"\r🔄 [{bar}] {progress}% - {status_msg}", end="", flush=True)
        
        time.sleep(0.5)
        
        # Timeout after 30 seconds for demo
        if time.time() - start_time > 30:
            print(f"\n⏰ Demo timeout reached")
            break
    
    print(f"\n\n✅ Task completed in {time.time() - start_time:.2f} seconds")
    
    if task.successful():
        result = task.result
        print("🎉 Task Result:")
        print(json.dumps(result, indent=2))
    elif task.failed():
        print(f"❌ Task failed: {task.info}")
    
    return task


def test_api_endpoints():
    """Test 2: API endpoint integration"""
    print("\n\n🌐 Test 2: API Endpoint Integration")
    print("=" * 50)
    
    base_url = "http://localhost:8001/api/v1"
    
    try:
        # Test health check
        print("🏥 Testing health check...")
        response = requests.get(f"{base_url}/async/jobs/health", timeout=5)
        if response.status_code == 200:
            health_data = response.json()
            print(f"✅ Health check passed: {health_data['status']}")
            print(f"📊 Celery workers: {health_data.get('celery_workers', 0)}")
        
    except requests.exceptions.RequestException as e:
        print(f"⚠️ API test skipped (server not running): {e}")
        return None


def test_worker_stats():
    """Test 3: Worker statistics"""
    print("\n\n📈 Test 3: Worker Statistics")
    print("=" * 50)
    
    try:
        # Get worker inspection
        inspect = celery_app.control.inspect()
        
        # Active tasks
        active_tasks = inspect.active()
        print(f"🏃 Active tasks: {len(active_tasks) if active_tasks else 0}")
        
        # Scheduled tasks
        scheduled_tasks = inspect.scheduled()
        print(f"⏰ Scheduled tasks: {len(scheduled_tasks) if scheduled_tasks else 0}")
        
        # Registered tasks
        registered_tasks = inspect.registered()
        if registered_tasks:
            for worker, tasks in registered_tasks.items():
                print(f"👷 Worker {worker}: {len(tasks)} registered tasks")
                for task_name in sorted(tasks)[:5]:  # Show first 5
                    print(f"   📋 {task_name}")
                if len(tasks) > 5:
                    print(f"   ... and {len(tasks) - 5} more")
        
        # Worker stats
        stats = inspect.stats()
        if stats:
            for worker, worker_stats in stats.items():
                print(f"\n📊 Worker {worker} stats:")
                print(f"   🔢 Pool processes: {worker_stats.get('pool', {}).get('processes', 'N/A')}")
                print(f"   💾 Total memory: {worker_stats.get('rusage', {}).get('maxrss', 'N/A')}")
        
    except Exception as e:
        print(f"⚠️ Worker stats error: {e}")


def test_queue_routing():
    """Test 4: Queue routing verification"""
    print("\n\n🚦 Test 4: Queue Routing Verification")
    print("=" * 50)
    
    # Test different task types to verify queue routing
    from app.tasks import ai_tasks, video_tasks, social_tasks, maintenance
    
    test_tasks = [
        ("AI Processing", ai_tasks.generate_image_with_ai, {"prompt": "Test AI", "model": "dall-e-3"}),
        ("Video Processing", video_tasks.process_video, {"video_path": "/test/video.mp4", "operations": ["normalize"]}),
        ("Social Media", social_tasks.publish_to_social_media, {"content_path": "/test/content.jpg", "platforms": ["twitter"], "caption": "Test post"}),
        ("Maintenance", maintenance.cleanup_temp_files, {})
    ]
    
    submitted_tasks = []
    
    for task_type, task_func, params in test_tasks:
        try:
            print(f"🚀 Submitting {task_type} task...")
            task = task_func.delay(**params)
            submitted_tasks.append((task_type, task))
            print(f"   ✅ Job ID: {task.id}")
            
            # Quick status check
            time.sleep(0.5)
            print(f"   📍 Status: {task.status}")
            
        except Exception as e:
            print(f"   ❌ Failed to submit {task_type}: {e}")
    
    print(f"\n📋 Total tasks submitted: {len(submitted_tasks)}")
    
    # Wait a bit and check final statuses
    print("\n⏳ Waiting 3 seconds for processing...")
    time.sleep(3)
    
    print("\n📊 Final task statuses:")
    for task_type, task in submitted_tasks:
        status = task.status
        if status == 'SUCCESS':
            emoji = "✅"
        elif status == 'FAILURE':
            emoji = "❌"
        elif status in ['PENDING', 'RETRY']:
            emoji = "⏳"
        else:
            emoji = "🔄"
        
        print(f"   {emoji} {task_type}: {status}")


def main():
    """Run complete async processing demonstration"""
    print("🎬 VideoAI Async Processing Demo")
    print("=" * 60)
    print("📋 This demo will test the complete async infrastructure:")
    print("   • Direct Celery task execution")
    print("   • Real-time progress monitoring")
    print("   • API endpoint integration")
    print("   • Worker statistics")
    print("   • Queue routing verification")
    print("=" * 60)
    
    # Run all tests
    test_celery_direct()
    test_api_endpoints()
    test_worker_stats()
    test_queue_routing()
    
    print("\n\n🎉 Demo completed!")
    print("🔍 Check the results above to verify async infrastructure")
    print("💡 To run individual tests, call the functions directly")


if __name__ == "__main__":
    main()
