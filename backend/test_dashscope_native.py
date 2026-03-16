import requests
import os
import sys
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

print(f"Testing DashScope native API with audio file")
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

# Try DashScope native API
print("="*60)
print("Testing DashScope native API")
print("="*60)

# Different possible endpoints
endpoints = [
    'https://dashscope.aliyuncs.com/api/v1/services/audio/asr/transcription',
    'https://dashscope.aliyuncs.com/api/v1/audio/asr',
    'https://dashscope.aliyuncs.com/api/v1/services/audio/transcription',
]

headers = {
    'Authorization': f'Bearer {api_key}',
    'Content-Type': 'application/json'
}

for endpoint in endpoints:
    print(f"\nTrying endpoint: {endpoint}")

    try:
        # Try with file upload
        files = {
            'file': ('audio.m4a', audio_data, 'audio/mp4')
        }
        data = {
            'model': 'paraformer-v2'
        }

        response = requests.post(
            endpoint,
            headers={'Authorization': f'Bearer {api_key}'},
            files=files,
            data=data,
            timeout=30
        )

        print(f"Response Status: {response.status_code}")
        print(f"Response Body: {response.text[:500]}")

        if response.status_code != 404:
            print("Found working endpoint!")
            break

    except Exception as e:
        print(f"Exception: {e}")

print("\n" + "="*60)
print("Testing completed")