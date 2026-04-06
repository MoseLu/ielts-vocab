import sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv()
from services.word_tts import synthesize_word_to_bytes
print('import OK')
print('Testing single word...')
audio = synthesize_word_to_bytes('hello')
print(f'audio len={len(audio)} bytes')
