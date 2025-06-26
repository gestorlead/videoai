#!/usr/bin/env python3
"""Simple Celery test"""

import time
from app.tasks.ai_tasks import generate_image_with_ai

# Submit a simple task
print("🚀 Submitting image generation task...")
task = generate_image_with_ai.delay(prompt="A robot artist", model="dall-e-3")
print(f"✅ Task ID: {task.id}")

# Monitor for 10 seconds
print("📊 Monitoring progress...")
for i in range(20):
    status = task.status
    print(f"   Status: {status}")
    
    if status == 'SUCCESS':
        print(f"🎉 Success! Result: {task.result}")
        break
    elif status == 'FAILURE':
        print(f"❌ Failed: {task.info}")
        break
    elif status == 'PROGRESS':
        info = task.info
        print(f"   Progress: {info.get('progress', 0)}% - {info.get('status', 'Processing...')}")
    
    time.sleep(0.5)

print("✅ Test completed!")
