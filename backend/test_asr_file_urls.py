import requests
import os
import sys
import json
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

print(f"Testing DashScope ASR API")
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

endpoint = 'https://dashscope.aliyuncs.com/api/v1/services/audio/asr/transcription'

headers = {
    'Authorization': f'Bearer {api_key}',
    'Content-Type': 'application/json'
}

# Try different models
models = [
    'paraformer-v2',
    'paraformer-8k-v1',
    'fun-asr-mtl-2025-08-25',
    'qwen3-asr-flash-filetrans'
]

for model in models:
    print("="*60)
    print(f"Testing model: {model}")
    print("="*60)

    # Upload file to get URL first, or use file_urls with OSS
    # For now, try with file_urls parameter pointing to a local file
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
            print("\n[SUCCESS]")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            break
        else:
            print(f"\n[FAILED]")

    except Exception as e:
        print(f"Exception: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "="*60)
print("Test completed")