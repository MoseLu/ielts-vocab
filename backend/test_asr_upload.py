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

print(f"Testing DashScope ASR API (Direct Upload)")
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

# Try direct file upload to different endpoints
endpoints = [
    ('https://dashscope.aliyuncs.com/api/v1/services/audio/asr/transcription', 'paraformer-v2'),
]

headers = {
    'Authorization': f'Bearer {api_key}'
}

for endpoint, model in endpoints:
    print("="*60)
    print(f"Testing: {endpoint}")
    print(f"Model: {model}")
    print("="*60)

    try:
        # Try with multipart/form-data
        files = {
            'file': ('audio.m4a', audio_data, 'audio/mp4')
        }
        data = {
            'model': model
        }

        response = requests.post(
            endpoint,
            headers=headers,
            files=files,
            data=data,
            timeout=30
        )

        print(f"Response Status: {response.status_code}")
        print(f"Response Body: {response.text}")

        if response.status_code == 200:
            result = response.json()
            print("\n[SUCCESS]")
            print(json.dumps(result, indent=2, ensure_ascii=False))
        elif response.status_code == 403:
            # Async mode required
            print("\n[INFO] Async mode required, trying with X-DashScope-Async header...")

            headers_async = {
                'Authorization': f'Bearer {api_key}',
                'X-DashScope-Async': 'enable'
            }

            # Try with file_urls parameter
            payload = {
                "model": model,
                "input": {
                    "file_urls": [
                        f"file://{os.path.abspath(audio_file_path)}"
                    ]
                }
            }

            response = requests.post(
                endpoint,
                headers=headers_async,
                json=payload,
                timeout=30
            )

            print(f"Async Response Status: {response.status_code}")
            print(f"Async Response Body: {response.text}")

        else:
            print(f"\n[FAILED]")

    except Exception as e:
        print(f"Exception: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "="*60)
print("Test completed")