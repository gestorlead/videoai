#!/usr/bin/env python3
"""Test task execution synchronously"""

from app.tasks.ai_tasks import generate_image_with_ai

# Test the task function directly (synchronously)
print("🧪 Testing task function directly (sync)...")
result = generate_image_with_ai(prompt="Test robot", model="dall-e-3")
print(f"✅ Sync result: {result}")

print("\n🚀 Now testing async...")
# Test async
task = generate_image_with_ai.delay(prompt="Test robot async", model="dall-e-3")
print(f"✅ Task submitted: {task.id}")
print(f"📍 Status: {task.status}")
