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
base_url = os.environ.get('DASHSCOPE_BASE_URL', 'https://dashscope.aliyuncs.com/compatible-mode/v1')

# Test with different ASR models
models_to_test = [
    'qwen3-asr-flash-filetrans',
    'fun-asr-mtl-2025-08-25',
    'fun-asr-flash-8k-realtime'
]

audio_file_path = r'C:\Users\12081\Documents\录音\录音 (4).m4a'

print(f"Testing DashScope ASR API with audio file: {audio_file_path}")
print(f"API Key: {api_key[:20]}...")
print(f"Base URL: {base_url}")
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

headers = {
    'Authorization': f'Bearer {api_key}'
}

for model in models_to_test:
    print(f"\n{'='*60}")
    print(f"Testing model: {model}")
    print('='*60)

    try:
        files = {
            'file': ('audio.m4a', audio_data, 'audio/mp4')
        }
        data = {
            'model': model
        }

        print(f"Sending request to: {base_url}/audio/transcriptions")
        response = requests.post(
            f'{base_url}/audio/transcriptions',
            headers=headers,
            files=files,
            data=data,
            timeout=30
        )

        print(f"Response Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Body: {response.text}")

        if response.status_code == 200:
            result = response.json()
            text = result.get('text', '')
            print(f"\n[SUCCESS] Recognized text: {text}")
            break
        else:
            print(f"\n[FAILED] Status {response.status_code}")
            try:
                error_data = response.json()
                print(f"Error details: {error_data}")
            except:
                print(f"Error text: {response.text}")

    except Exception as e:
        print(f"\n[EXCEPTION] {e}")
        import traceback
        traceback.print_exc()

print("\n" + "="*60)
print("Test completed")