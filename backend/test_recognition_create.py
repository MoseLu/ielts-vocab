import os
from pathlib import Path
from dotenv import load_dotenv
import dashscope
from dashscope.audio.asr import Recognition, RecognitionCallback, RecognitionResult

# Load .env
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

# Configure DashScope
dashscope.api_key = os.environ.get('DASHSCOPE_API_KEY', '')
dashscope.base_websocket_api_url = 'wss://dashscope.aliyuncs.com/api-ws/v1/inference'

model = 'fun-asr-realtime'

# Test creating Recognition object
class TestCallback(RecognitionCallback):
    def on_event(self, result: RecognitionResult):
        print(f"Event: {result.get_sentence()}")

    def on_complete(self):
        print("Complete")

    def on_error(self, message):
        print(f"Error: {message}")

try:
    callback = TestCallback()
    recognition = Recognition(
        model=model,
        callback=callback,
        format='wav',
        sample_rate=16000
    )
    print("SUCCESS: Recognition object created successfully!")
    print(f"Model: {recognition.model}")
    print(f"Format: {recognition.format}")
    print(f"Sample rate: {recognition.sample_rate}")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()