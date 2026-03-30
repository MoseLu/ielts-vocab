import os, requests

key1 = os.environ.get('MINIMAX_API_KEY', 'sk-cp-JHl5IpVtLuCywAIZ41BJwHCCXf_toYtgB4hy583Y6lPC3E-Q7x2PY1ytcuVZnUV7udsWLDEc2kh8WSDWFTRHfN_h53MpaFhMh-wC4R3tnl_Mf-Zl4e_-E2c')
key2 = os.environ.get('MINIMAX_API_KEY_2', 'sk-cp-dRuHp8lYwGJT3nehNlcVvBnfsmfcbzKm2haQa1PrRXfrJS0lyyRayL1O1jaC6a55iO9cxO3YlhDhgsBoykP-vBW8oA9LXATkHx0W4P30ktGsxcmrpsbk6OY')
url = os.environ.get('MINIMAX_TTS_BASE_URL', 'https://api.minimaxi.com')

failed_words = ['fossil', 'formal', 'foundation', 'found', 'fountain', 'fourth', 'founder', 'foster', 'somebody', 'solo', 'solve', 'some', 'someone', 'soluble']

for word in failed_words:
    for label, key, voice in [
        ('key1_Trustworthy', key1, 'English_Trustworthy_Man'),
        ('key2_Graceful', key2, 'English_Graceful_Lady'),
        ('key1_Diligent', key1, 'English_Diligent_Man'),
        ('key2_Aussie', key2, 'English_Aussie_Bloke'),
    ]:
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
                print(f'{word} + {voice}: OK')
            else:
                print(f'{word} + {voice}: error {code} {d.get("base_resp", {}).get("status_msg", "")}')
        else:
            print(f'{word} + {voice}: HTTP {resp.status_code}')
