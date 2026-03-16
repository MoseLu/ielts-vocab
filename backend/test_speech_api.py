import requests
import os
from dotenv import load_dotenv

# Load .env
load_dotenv()

api_key = os.environ.get('DASHSCOPE_API_KEY', '')
base_url = os.environ.get('DASHSCOPE_BASE_URL', 'https://dashscope.aliyuncs.com/compatible-mode/v1')
model = 'fun-asr-mtl-2025-08-25'

print(f"Testing DashScope ASR API...")
print(f"API Key: {api_key[:20]}...")
print(f"Base URL: {base_url}")
print(f"Model: {model}")
print()

# Test with a simple text-to-speech first
# Since we don't have a real audio file, let's test the endpoint structure

headers = {
    'Authorization': f'Bearer {api_key}'
}

# Test endpoint
print("Testing API endpoint connectivity...")
try:
    # Create a dummy audio file for testing
    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
        # Create minimal wav file header (just for testing)
        tmp.write(b'RIFF' + b'\x00' * 100)
        tmp_path = tmp.name

    with open(tmp_path, 'rb') as f:
        files = {
            'file': ('test.wav', f, 'audio/wav')
        }
        data = {
            'model': model
        }

        response = requests.post(
            f'{base_url}/audio/transcriptions',
            headers=headers,
            files=files,
            data=data,
            timeout=10
        )

        print(f"Response Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Body: {response.text}")

    os.unlink(tmp_path)

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()