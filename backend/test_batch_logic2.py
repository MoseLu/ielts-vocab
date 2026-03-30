import sys, os, time
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv()

from services.word_tts import (
    synthesize_word_to_bytes, word_tts_data_dir,
    word_tts_cache_path
)
import hashlib

cache_dir = word_tts_data_dir()
print(f'cache_dir={cache_dir}')

# Simulate what the batch does: normalize key, call synthesize, write cache
test_word = 'hello'
normalized = test_word.strip().lower()
key = hashlib.md5(f'w:{normalized}:speech-2.8-hd:English_Trustworthy_Man'.encode()).hexdigest()[:16]
out_path = cache_dir / f'{key}.mp3'
print(f'word={test_word}, key={key}, out_path={out_path}')
print(f'already exists={out_path.exists()}')

print(f'Synthesizing...')
t0 = time.time()
audio = synthesize_word_to_bytes(test_word)
print(f'Got {len(audio)} bytes in {time.time()-t0:.1f}s')

cache_dir.mkdir(parents=True, exist_ok=True)
out_path.write_bytes(audio)
print(f'Wrote {out_path.stat().st_size} bytes')
