import os
import tempfile
import subprocess
from pathlib import Path
from dotenv import load_dotenv
import dashscope
from dashscope.audio.asr import Recognition, RecognitionCallback, RecognitionResult
import imageio_ffmpeg

# Load .env
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

# Configure DashScope
dashscope.api_key = os.environ.get('DASHSCOPE_API_KEY', '')
dashscope.base_websocket_api_url = 'wss://dashscope.aliyuncs.com/api-ws/v1/inference'

# Get FFmpeg executable
FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()

# Test audio file
audio_file = r'C:\Users\12081\Documents\录音\录音 (4).m4a'

print("Testing DashScope ASR with audio file...")
print(f"Audio file: {audio_file}")
print()

# Convert to WAV
wav_path = tempfile.mktemp(suffix='.wav')
result = subprocess.run(
    [FFMPEG_EXE, '-i', audio_file, '-ar', '16000', '-ac', '1', '-f', 'wav', wav_path, '-y'],
    capture_output=True,
    text=True,
    timeout=30
)

if result.returncode != 0:
    print(f"FFmpeg error: {result.stderr}")
    exit(1)

print(f"Converted to WAV: {wav_path}")

# Read audio
with open(wav_path, 'rb') as f:
    audio_data = f.read()

print(f"Audio size: {len(audio_data)} bytes")
print()

# Create callback
result_text = []

class TestCallback(RecognitionCallback):
    def on_event(self, result: RecognitionResult):
        sentence = result.get_sentence()
        print(f"Event received: {sentence}")
        if 'text' in sentence:
            result_text.append(sentence['text'])
            if RecognitionResult.is_sentence_end(sentence):
                print(f"Final: {sentence['text']}")

    def on_complete(self):
        print("Recognition complete")

    def on_error(self, message):
        print(f"Error: {message}")

# Create recognition
callback = TestCallback()
recognition = Recognition(
    model='fun-asr-realtime',
    callback=callback,
    format='wav',
    sample_rate=16000
)

print("Starting recognition...")

# Start
recognition.start()

# Send audio in chunks
chunk_size = 3200
offset = 0
count = 0
while offset < len(audio_data):
    chunk = audio_data[offset:offset + chunk_size]
    recognition.send_audio_frame(chunk)
    offset += chunk_size
    count += 1

print(f"Sent {count} chunks")

# Stop
recognition.stop()

print()
print("Result:", ' '.join(result_text))

# Cleanup
os.unlink(wav_path)