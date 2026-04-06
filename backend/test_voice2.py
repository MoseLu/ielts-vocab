import os, requests

key2 = os.environ.get('MINIMAX_API_KEY_2', 'sk-cp-dRuHp8lYwGJT3nehNlcVvBnfsmfcbzKm2haQa1PrRXfrJS0lyyRayL1O1jaC6a55iO9cxO3YlhDhgsBoykP-vBW8oA9LXATkHx0W4P30ktGsxcmrpsbk6OY')
url = os.environ.get('MINIMAX_TTS_BASE_URL', 'https://api.minimaxi.com')

test_cases = [
    ('key1_Trustworthy', 'sk-cp-JHl5IpVtLuCywAIZ41BJwHCCXf_toYtgB4hy583Y6lPC3E-Q7x2PY1ytcuVZnUV7udsWLDEc2kh8WSDWFTRHfN_h53MpaFhMh-wC4R3tnl_Mf-Zl4e_-E2c', 'English_Trustworthy_Man', 'fossil'),
    ('key2_Graceful', key2, 'English_Graceful_Lady', 'fossil'),
    ('key2_Trustworthy', key2, 'English_Trustworthy_Man', 'fossil'),
    ('key2_Graceful', key2, 'English_Graceful_Lady', 'foundation'),
]

for label, key, voice, word in test_cases:
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
            print(f'{label} + {word}: OK')
        else:
            print(f'{label} + {word}: API error {code}: {d.get("base_resp", {}).get("status_msg", "")}')
    else:
        print(f'{label} + {word}: HTTP {resp.status_code}')
