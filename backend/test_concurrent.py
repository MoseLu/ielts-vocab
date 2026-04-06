import os, requests, threading, time

key1 = os.environ.get('MINIMAX_API_KEY', 'sk-cp-JHl5IpVtLuCywAIZ41BJwHCCXf_toYtgB4hy583Y6lPC3E-Q7x2PY1ytcuVZnUV7udsWLDEc2kh8WSDWFTRHfN_h53MpaFhMh-wC4R3tnl_Mf-Zl4e_-E2c')
key2 = os.environ.get('MINIMAX_API_KEY_2', 'sk-cp-dRuHp8lYwGJT3nehNlcVvBnfsmfcbzKm2haQa1PrRXfrJS0lyyRayL1O1jaC6a55iO9cxO3YlhDhgsBoykP-vBW8oA9LXATkHx0W4P30ktGsxcmrpsbk6OY')
url = os.environ.get('MINIMAX_TTS_BASE_URL', 'https://api.minimaxi.com')

results = {'ok': 0, '2054': 0, 'other': 0}
lock = threading.Lock()

def call_tts(key, voice, word, idx):
    payload = {
        'model': 'speech-2.8-hd',
        'text': word,
        'stream': False,
        'voice_setting': {'voice_id': voice, 'speed': 1.0, 'vol': 1.0, 'pitch': 0, 'emotion': 'neutral'},
        'audio_setting': {'sample_rate': 32000, 'bitrate': 128000, 'format': 'mp3', 'channel': 1}
    }
    resp = requests.post(f'{url}/v1/t2a_v2', headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'}, json=payload, timeout=30)
    with lock:
        if resp.status_code == 200:
            d = resp.json()
            code = d.get('base_resp', {}).get('status_code')
            if code == 0:
                results['ok'] += 1
            elif code == 2054:
                results['2054'] += 1
                print(f'  [2054] thread={idx} word={word} voice={voice}')
            else:
                results['other'] += 1
                print(f'  [other {code}] thread={idx} word={word}')
        else:
            results['other'] += 1
            print(f'  [HTTP {resp.status_code}] thread={idx} word={word}')

# Test with 8 concurrent threads hitting BOTH keys
test_words = ['fossil', 'formal', 'foundation', 'found', 'fountain', 'fourth', 'founder', 'foster'] * 4
threads = []
for i, w in enumerate(test_words):
    key = key1 if i % 2 == 0 else key2
    voice = 'English_Trustworthy_Man' if i % 2 == 0 else 'English_Graceful_Lady'
    t = threading.Thread(target=call_tts, args=(key, voice, w, i))
    threads.append(t)

start = time.time()
for t in threads:
    t.start()
for t in threads:
    t.join()
elapsed = time.time() - start

print(f'\nResults: {results} in {elapsed:.1f}s')
