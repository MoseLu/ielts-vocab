import os, requests

key = os.environ.get('MINIMAX_API_KEY', 'sk-cp-JHl5IpVtLuCywAIZ41BJwHCCXf_toYtgB4hy583Y6lPC3E-Q7x2PY1ytcuVZnUV7udsWLDEc2kh8WSDWFTRHfN_h53MpaFhMh-wC4R3tnl_Mf-Zl4e_-E2c')
url = os.environ.get('MINIMAX_TTS_BASE_URL', 'https://api.minimaxi.com')

test_words = ['hello', 'critical', 'formal', 'get', 'give', 'gentle', 'forest', 'form']
for w in test_words:
    payload = {
        'model': 'speech-2.8-hd',
        'text': w,
        'stream': False,
        'voice_setting': {
            'voice_id': 'English_Trustworthy_Man',
            'speed': 1.0,
            'vol': 1.0,
            'pitch': 0,
            'emotion': 'neutral'
        },
        'audio_setting': {
            'sample_rate': 32000,
            'bitrate': 128000,
            'format': 'mp3',
            'channel': 1
        }
    }
    resp = requests.post(f'{url}/v1/t2a_v2', headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'}, json=payload, timeout=30)
    if resp.status_code == 200:
        d = resp.json()
        code = d.get('base_resp', {}).get('status_code')
        if code == 0:
            audio_hex = d.get('data', {}).get('audio', '')
            print(f'{w}: OK, audio hex len={len(audio_hex)}')
        else:
            print(f'{w}: API error {code}: {d.get("base_resp", {}).get("status_msg", "")}')
    else:
        print(f'{w}: HTTP {resp.status_code}')
