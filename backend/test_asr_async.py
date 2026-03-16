import requests
import os
import sys
import json
import time
from dotenv import load_dotenv

# Fix encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Load .env
load_dotenv()

api_key = os.environ.get('DASHSCOPE_API_KEY', '')

audio_file_path = r'C:\Users\12081\Documents\录音\录音 (4).m4a'

print(f"Testing DashScope ASR API (Async)")
print(f"API Key: {api_key[:20]}...")
print()

# Check if file exists
if not os.path.exists(audio_file_path):
    print(f"Error: Audio file not found: {audio_file_path}")
    sys.exit(1)

# Read audio file
with open(audio_file_path, 'rb') as f:
    audio_data = f.read()

print(f"Audio file size: {len(audio_data)} bytes")
print()

# Step 1: Submit transcription task
endpoint = 'https://dashscope.aliyuncs.com/api/v1/services/audio/asr/transcription'

headers = {
    'Authorization': f'Bearer {api_key}',
    'Content-Type': 'application/json',
    'X-DashScope-Async': 'enable'  # Enable async mode
}

model = 'paraformer-v2'

print("="*60)
print(f"Step 1: Submitting transcription task with model: {model}")
print("="*60)

payload = {
    "model": model,
    "input": {
        "file_urls": [
            f"file://{os.path.abspath(audio_file_path)}"
        ]
    }
}

try:
    response = requests.post(
        endpoint,
        headers=headers,
        json=payload,
        timeout=30
    )

    print(f"Response Status: {response.status_code}")
    print(f"Response Body: {response.text}")

    if response.status_code == 200:
        result = response.json()
        task_id = result.get('output', {}).get('task_id')

        if task_id:
            print(f"\n[SUCCESS] Task submitted. Task ID: {task_id}")

            # Step 2: Poll for results
            print("\n" + "="*60)
            print("Step 2: Polling for results...")
            print("="*60)

            # Try different query URLs
            query_urls = [
                f"https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}",
                f"{endpoint}?task_id={task_id}",
            ]

            found = False
            for query_url in query_urls:
                if found:
                    break

                print(f"\nTrying query URL: {query_url}")

                for i in range(5):
                    time.sleep(2)
                    print(f"\nPolling attempt {i+1}/5...")

                    try:
                        query_response = requests.get(
                            query_url,
                            headers={'Authorization': f'Bearer {api_key}'}
                        )

                        print(f"Query Status: {query_response.status_code}")
                        print(f"Query Response: {query_response.text}")

                        if query_response.status_code == 200:
                            query_result = query_response.json()
                            task_status = query_result.get('output', {}).get('task_status')

                            print(f"Task Status: {task_status}")

                            if task_status == 'SUCCEEDED':
                                transcription_result = query_result.get('output', {}).get('results', [])
                                if transcription_result:
                                    text = transcription_result[0].get('transcription_text', '')
                                    print(f"\n[SUCCESS] Transcription completed!")
                                    print(f"Result: {text}")
                                found = True
                                break
                            elif task_status == 'FAILED':
                                print(f"\n[FAILED] Task failed")
                                break
                    except Exception as e:
                        print(f"Query error: {e}")
                        break
        else:
            print("[ERROR] No task_id in response")
    else:
        print(f"\n[FAILED] Submit task failed")

except Exception as e:
    print(f"Exception: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
print("Test completed")