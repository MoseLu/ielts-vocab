import os, requests, threading, time

key1 = os.environ.get('MINIMAX_API_KEY', 'sk-cp-JHl5IpVtLuCywAIZ41BJwHCCXf_toYtgB4hy583Y6lPC3E-Q7x2PY1ytcuVZnUV7udsWLDEc2kh8WSDWFTRHfN_h53MpaFhMh-wC4R3tnl_Mf-Zl4e_-E2c')
key2 = os.environ.get('MINIMAX_API_KEY_2', 'sk-cp-dRuHp8lYwGJT3nehNlcVvBnfsmfcbzKm2haQa1PrRXfrJS0lyyRayL1O1jaC6a55iO9cxO3YlhDhgsBoykP-vBW8oA9LXATkHx0W4P30ktGsxcmrpsbk6OY')
url = os.environ.get('MINIMAX_TTS_BASE_URL', 'https://api.minimaxi.com')

results = {'ok': 0, '2054': 0, 'other': 0, 'errors': []}
lock = threading.Lock()

# Replicate the exact semaphore logic from word_tts.py
_MINIMAX_API_KEYS = [key1, key2]
_MINIMAX_KEY_SEMS = {key1: threading.Semaphore(2), key2: threading.Semaphore(2)}
_MINIMAX_GLOBAL_SEM = threading.Semaphore(4)
_MINIMAX_KEY_VOICES = {key1: 'English_Trustworthy_Man', key2: 'English_Graceful_Lady'}
_minimax_keys_randomized = []

def _init():
    import random
    global _minimax_keys_randomized
    _minimax_keys_randomized = _MINIMAX_API_KEYS[:]
    random.shuffle(_minimax_keys_randomized)

_init()

def _get_key_with_sem():
    _MINIMAX_GLOBAL_SEM.acquire(blocking=True)
    try:
        if not _minimax_keys_randomized:
            _init()
        while _minimax_keys_randomized:
            key = _minimax_keys_randomized.pop()
            per_key_sem = _MINIMAX_KEY_SEMS[key]
            if per_key_sem.acquire(blocking=False):
                return key, per_key_sem
            _minimax_keys_randomized.insert(0, key)
        key = _MINIMAX_API_KEYS[0]
        per_key_sem = _MINIMAX_KEY_SEMS[key]
        per_key_sem.acquire()
        return key, per_key_sem
    except Exception:
        _MINIMAX_GLOBAL_SEM.release()
        raise

def call_tts(word, idx):
    try:
        key, per_key_sem = _get_key_with_sem()
        voice = _MINIMAX_KEY_VOICES[key]
        try:
            payload = {
                'model': 'speech-2.8-hd',
                'text': word,
                'stream': False,
                'voice_setting': {'voice_id': voice, 'speed': 1.0, 'vol': 1.0, 'pitch': 0, 'emotion': 'neutral'},
                'audio_setting': {'sample_rate': 32000, 'bitrate': 128000, 'format': 'mp3', 'channel': 1}
            }
            resp = requests.post(f'{url}/v1/t2a_v2', headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'}, json=payload, timeout=30)
            if resp.status_code == 200:
                d = resp.json()
                code = d.get('base_resp', {}).get('status_code')
                if code == 0:
                    with lock: results['ok'] += 1
                elif code == 2054:
                    with lock:
                        results['2054'] += 1
                        results['errors'].append(f'{word}+{voice}')
                else:
                    with lock: results['other'] += 1
            else:
                with lock: results['other'] += 1
        finally:
            per_key_sem.release()
            _MINIMAX_GLOBAL_SEM.release()
    except Exception as e:
        with lock: results['errors'].append(str(e))

global_sem = _MINIMAX_GLOBAL_SEM  # expose for release

# Use the exact words that failed in batch: fully, functionally, fund, fun, functional...
failed_words = ['fully', 'functionally', 'fund', 'fun', 'functional', 'functions',
                'fundamental', 'fume', 'functioning', 'function', 'functioned',
                'fumes', 'fundamentally', 'funded', 'funding', 'funds',
                'funeral', 'funny', 'fungus', 'fur', 'furnace', 'furious']

# Run 12 threads like the batch
threads = []
for i, w in enumerate(failed_words * 1):  # 1x each = 22 threads
    t = threading.Thread(target=call_tts, args=(w, i))
    threads.append(t)

start = time.time()
for t in threads: t.start()
for t in threads: t.join()
elapsed = time.time() - start

print(f'Results: {results} in {elapsed:.1f}s')
print(f'Errors: {results["errors"][:10]}')
