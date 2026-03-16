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

print(f"Testing DashScope Realtime ASR API")
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

# Try realtime ASR endpoints
endpoints = [
    'https://dashscope.aliyuncs.com/api/v1/services/audio/asr/realtime',
    'https://dashscope.aliyuncs.com/api/v1/services/audio/asr/streaming',
]

headers = {
    'Authorization': f'Bearer {api_key}'
}

models = [
    'fun-asr-flash-8k-realtime',
]

for endpoint in endpoints:
    for model in models:
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
                sys.exit(0)

        except Exception as e:
            print(f"Exception: {e}")
            import traceback
            traceback.print_exc()

print("\n" + "="*60)
print("All tests completed")