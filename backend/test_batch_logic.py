import sys, os, time
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv()
from services.word_tts import synthesize_word_to_bytes, _MINIMAX_GLOBAL_SEM, _MINIMAX_KEY_SEMS

print(f'global_sem._value={_MINIMAX_GLOBAL_SEM._value}')
for k, v in _MINIMAX_KEY_SEMS.items():
    print(f'key_sem {k[:20]}... = {v._value}')

print('Testing synthesize...')
t0 = time.time()
audio = synthesize_word_to_bytes('hello')
print(f'OK: {len(audio)} bytes in {time.time()-t0:.1f}s')
