import os, requests, threading, time

key1 = os.environ.get('MINIMAX_API_KEY', 'sk-cp-JHl5IpVtLuCywAIZ41BJwHCCXf_toYtgB4hy583Y6lPC3E-Q7x2PY1ytcuVZnUV7udsWLDEc2kh8WSDWFTRHfN_h53MpaFhMh-wC4R3tnl_Mf-Zl4e_-E2c')
key2 = os.environ.get('MINIMAX_API_KEY_2', 'sk-cp-dRuHp8lYwGJT3nehNlcVvBnfsmfcbzKm2haQa1PrRXfrJS0lyyRayL1O1jaC6a55iO9cxO3YlhDhgsBoykP-vBW8oA9LXATkHx0W4P30ktGsxcmrpsbk6OY')
url = os.environ.get('MINIMAX_TTS_BASE_URL', 'https://api.minimaxi.com')

results = {'k1_ok': 0, 'k2_ok': 0, 'k1_err': 0, 'k2_err': 0}
lock = threading.Lock()

def call(key, label, word, idx):
    payload = {
        'model': 'speech-2.8-hd',
        'text': word,
        'stream': False,
        'voice_setting': {'voice_id': 'English_Trustworthy_Man', 'speed': 1.0, 'vol': 1.0, 'pitch': 0, 'emotion': 'neutral'},
        'audio_setting': {'sample_rate': 32000, 'bitrate': 128000, 'format': 'mp3', 'channel': 1}
    }
    t0 = time.time()
    resp = requests.post(f'{url}/v1/t2a_v2', headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'}, json=payload, timeout=30)
    elapsed = time.time() - t0
    with lock:
        if resp.status_code == 200:
            d = resp.json()
            code = d.get('base_resp', {}).get('status_code')
            if code == 0:
                if label == 'k1': results['k1_ok'] += 1
                else: results['k2_ok'] += 1
            else:
                if label == 'k1': results['k1_err'] += 1
                else: results['k2_err'] += 1
                print(f'[{label}] error {code}: {d.get("base_resp",{}).get("status_msg","")} word={word}')
        else:
            print(f'[{label}] HTTP {resp.status_code} word={word} elapsed={elapsed:.1f}s')
            if label == 'k1': results['k1_err'] += 1
            else: results['k2_err'] += 1

# Test: fire 30 concurrent requests at EACH key simultaneously (total 60 concurrent)
words = [f'word{i}' for i in range(30)]
threads = []
for i, w in enumerate(words):
    threads.append(threading.Thread(target=call, args=(key1, 'k1', w, i)))
    threads.append(threading.Thread(target=call, args=(key2, 'k2', w, i)))

start = time.time()
for t in threads: t.start()
for t in threads: t.join()
elapsed = time.time() - start

print(f'\nResults: {results} in {elapsed:.1f}s')
print(f'k1 rate: {results["k1_ok"]/elapsed*60:.1f} req/min, k2 rate: {results["k2_ok"]/elapsed*60:.1f} req/min')
