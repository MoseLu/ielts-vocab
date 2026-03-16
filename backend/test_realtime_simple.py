import requests
import os
import sys
from dotenv import load_dotenv

# Load .env
load_dotenv()

api_key = os.environ.get('DASHSCOPE_API_KEY', '')

# Test audio file
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

# Test realtime endpoint
endpoint = 'https://dashscope.aliyuncs.com/api/v1/services/audio/asr/realtime'

models = [
    'fun-asr-flash-8k-realtime',
    'qwen3-asr-flash-realtime',
]

headers = {
    'Authorization': f'Bearer {api_key}'
}

for model in models:
    print("="*60)
    print(f"Testing model: {model}")
    print("="*60)

    try:
        # Try with multipart/form-data
        files = {
            'file': ('audio.m4a', audio_data, 'audio/mp4')
        }
        data = {
            'model': model,
            'format': 'm4a',
            'sample_rate': 16000
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
            print(f"Result: {result}")
            break
        else:
            print(f"\n[FAILED]")

    except Exception as e:
        print(f"Exception: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "="*60)
print("Test completed")