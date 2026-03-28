"""
MiniMax TTS (Text-to-Speech) 路由
使用 MiniMax Speech-01 系列模型生成高质量英语例句音频
本地缓存：相同 sentence + voice 只调用一次 API，之后直接读文件
"""

import os
import io
import hashlib
from pathlib import Path
from flask import Blueprint, request, jsonify, send_file, current_app
from dotenv import load_dotenv
from routes.middleware import admin_required

# Load .env from backend directory
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

tts_bp = Blueprint('tts', __name__)


def add_pause_tags(text: str, pause_seconds: float = 0.3) -> str:
    """
    在标点符号处插入 MiniMax TTS 的停顿标签 <#x#>
    使句子有自然的停顿，模拟雅思听力的节奏

    MiniMax TTS 支持 <#x#> 标签插入 x 秒的停顿
    """
    import re
    pause_tag = f"<#{pause_seconds}#>"

    # 在逗号后插入短暂停顿
    text = re.sub(r',(\s*)', f',{pause_tag}\\1', text)

    # 在句号/感叹号/问号后插入较长停顿
    text = re.sub(r'([.!?])(\s+)', f'{pause_tag}\\1\\2', text)

    # 在分号后插入中等停顿
    text = re.sub(r';(\s*)', f';{pause_tag}\\1', text)

    return text


# MiniMax TTS API configuration
MINIMAX_API_KEY = os.environ.get('MINIMAX_API_KEY', '')
MINIMAX_API_KEY_2 = os.environ.get('MINIMAX_API_KEY_2', '')
MINIMAX_BASE_URL = os.environ.get('MINIMAX_TTS_BASE_URL', 'https://api.minimaxi.com')

# Track which key to use (round-robin)
_use_secondary_key = False

# Alternating voice IDs for example audio (Trustworthy Man + Serene Woman)
_ALTERNATING_VOICES = ['English_Trustworthy_Man', 'Serene_Woman']
_alternating_voice_index = 0


def _get_api_key():
    """Get API key with simple round-robin."""
    global _use_secondary_key
    if MINIMAX_API_KEY_2 and _use_secondary_key:
        _use_secondary_key = not _use_secondary_key
        return MINIMAX_API_KEY_2
    elif MINIMAX_API_KEY:
        _use_secondary_key = not _use_secondary_key
        return MINIMAX_API_KEY
    else:
        return MINIMAX_API_KEY_2 or ''


# 可用的英文语音列表 (雅思场景适合的清晰、自然语音)
ENGLISH_VOICES = {
    'English_Trustworthy_Man': 'English_Trustworthy_Man',   # 可靠男声 - 英式英语
    'Serene_Woman': 'Serene_Woman',                         # 宁静女声 - 清晰自然
    'male-qn-qingse': 'male-qn-qingse',                    # 清涩男声
    'female-tianmei': 'female-tianmei',                     # 天美女声
}

# 推荐的雅思听力风格语音 (清晰，自然、适中语速)
RECOMMENDED_VOICES = [
    'English_Trustworthy_Man',   # 可靠男声 - 英式英语
    'Serene_Woman',             # 宁静女声 - 清晰自然
]


# ── Local cache ────────────────────────────────────────────────────────────────

def _cache_dir() -> Path:
    d = Path(__file__).parent.parent / 'tts_cache'
    d.mkdir(exist_ok=True)
    return d


def _cache_path(sentence: str, voice_id: str) -> Path:
    """Return local cache file path for (sentence, voice_id)."""
    key = hashlib.md5(f"ex:{sentence}:{voice_id}".encode()).hexdigest()[:16]
    return _cache_dir() / f'{key}.mp3'


@tts_bp.route('/voices', methods=['GET'])
def list_voices():
    """列出所有可用的英文语音"""
    return jsonify({
        'voices': [
            {'id': vid, 'name': vid}
            for vid in ENGLISH_VOICES.keys()
        ],
        'recommended': RECOMMENDED_VOICES
    })


@tts_bp.route('/generate', methods=['POST'])
def generate_speech():
    """
    使用 MiniMax TTS 生成音频

    请求体:
    {
        "text": "The accomplishment of this task took much effort.",
        "voice_id": "English_Trustworthy_Man",  // 可选，默认使用推荐语音
        "speed": 1.0,                    // 可选，默认 1.0
        "emotion": "neutral",             // 可选: neutral, happy, sad, angry
        "model": "speech-01-turbo"       // 可选: speech-01-hd (高质量), speech-01-turbo (快速)
    }

    返回: MP3 音频文件
    """
    data = request.get_json() or {}
    text = (data.get('text') or '').strip()

    if not text:
        return jsonify({'error': 'text is required'}), 400

    # 参数
    voice_id = data.get('voice_id', 'English_Trustworthy_Man')
    speed = float(data.get('speed', 1.0))
    emotion = data.get('emotion', 'neutral')
    model = data.get('model', 'speech-01-turbo')

    # 验证语音 ID
    if voice_id not in ENGLISH_VOICES:
        return jsonify({
            'error': f'Invalid voice_id. Available: {list(ENGLISH_VOICES.keys())}'
        }), 400

    # 生成缓存 key (基于文本和参数的 hash)
    cache_key = hashlib.md5(
        f"{text}:{voice_id}:{speed}:{emotion}:{model}".encode()
    ).hexdigest()[:16]

    # 尝试本地缓存
    cached = _cache_path(text + f":{speed}:{emotion}:{model}", voice_id)
    if cached.exists():
        return send_file(cached, mimetype='audio/mpeg', as_attachment=False,
                        download_name=f'tts_{cache_key}.mp3')

    try:
        import requests
        api_key = _get_api_key()
        url = f"{MINIMAX_BASE_URL}/v1/t2a_v2"

        payload = {
            "model": model,
            "text": text,
            "stream": False,
            "voice_setting": {
                "voice_id": voice_id,
                "speed": speed,
                "vol": 1.0,
                "pitch": 0,
                "emotion": emotion
            },
            "audio_setting": {
                "sample_rate": 32000,
                "bitrate": 128000,
                "format": "mp3",
                "channel": 1
            }
        }

        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }

        print(f"\n=== MiniMax TTS Request ===")
        print(f"Model: {model}")
        print(f"Voice: {voice_id}")
        print(f"Speed: {speed}")
        print(f"Emotion: {emotion}")
        print(f"Text: {text[:100]}...")

        resp = requests.post(url, headers=headers, json=payload, timeout=30)

        if resp.status_code == 200:
            # 返回 MP3 音频
            audio_data = io.BytesIO(resp.content)
            audio_data.seek(0)
            return send_file(
                audio_data,
                mimetype='audio/mpeg',
                as_attachment=False,
                download_name=f'tts_{cache_key}.mp3'
            )
        elif resp.status_code == 429:
            print(f"TTS rate limited: {resp.text}")
            return jsonify({
                'error': 'TTS quota exceeded. Please try again later.',
                'details': resp.text
            }), 429
        else:
            print(f"TTS error {resp.status_code}: {resp.text}")
            return jsonify({'error': f'TTS generation failed: {resp.text}'}), resp.status_code

    except requests.exceptions.Timeout:
        return jsonify({'error': 'TTS request timeout'}), 504
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'TTS error: {str(e)}'}), 500


@tts_bp.route('/example-audio', methods=['POST'])
def generate_example_audio():
    """
    生成例句音频的专用端点
    专为雅思例句优化: 清晰，自然、适中语速

    本地缓存策略:
    - 缓存 key = sentence hash + voice_id（不同 voice 分别缓存）
    - 首次生成后存到 backend/tts_cache/，之后直接读文件（零 API 调用）

    请求体:
    {
        "sentence": "The accomplishment of this task took much effort.",
        "word": "accomplishment"  // 可选，用于缓存 key
    }
    """
    data = request.get_json() or {}
    sentence = (data.get('sentence') or '').strip()
    word = (data.get('word') or '').strip()

    if not sentence:
        return jsonify({'error': 'sentence is required'}), 400

    # 添加停顿标签，使句子有自然的节奏和停顿
    sentence_with_pauses = add_pause_tags(sentence, pause_seconds=0.4)

    # 交替使用两种语音
    global _alternating_voice_index
    voice_id = _ALTERNATING_VOICES[_alternating_voice_index]
    _alternating_voice_index = (_alternating_voice_index + 1) % len(_ALTERNATING_VOICES)

    # 缓存路径：sentence + voice_id 作为 key
    cache_key = hashlib.md5(f"ex:{sentence}:{voice_id}".encode()).hexdigest()[:16]
    cached_file = _cache_dir() / f'{cache_key}.mp3'

    # 命中缓存 → 直接返回本地文件
    if cached_file.exists():
        print(f"[TTS Cache HIT] {cached_file.name} (voice={voice_id})")
        return send_file(cached_file, mimetype='audio/mpeg', as_attachment=False,
                        download_name=f'example_{cache_key}.mp3')

    print(f"[TTS Cache MISS] voice={voice_id}, sentence={sentence[:60]}...")

    try:
        import requests
        api_key = _get_api_key()
        url = f"{MINIMAX_BASE_URL}/v1/t2a_v2"

        payload = {
            "model": "speech-2.8-hd",
            "text": sentence_with_pauses,
            "stream": False,
            "voice_setting": {
                "voice_id": voice_id,
                "speed": 0.9,
                "vol": 1.0,
                "pitch": 0,
                "emotion": "neutral"
            },
            "audio_setting": {
                "sample_rate": 32000,
                "bitrate": 128000,
                "format": "mp3",
                "channel": 1
            }
        }

        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }

        resp = requests.post(url, headers=headers, json=payload, timeout=30)

        if resp.status_code == 200:
            resp_data = resp.json()
            audio_hex = resp_data.get('data', {}).get('audio')
            if not audio_hex:
                return jsonify({'error': 'No audio in response', 'response': resp_data}), 500

            # 解码 hex 音频数据
            audio_bytes = bytes.fromhex(audio_hex)

            # 保存到本地缓存
            with open(cached_file, 'wb') as f:
                f.write(audio_bytes)
            print(f"[TTS Cache SAVED] {cached_file.name} ({len(audio_bytes)} bytes)")

            # 返回音频
            audio_data = io.BytesIO(audio_bytes)
            audio_data.seek(0)
            return send_file(
                audio_data,
                mimetype='audio/mpeg',
                as_attachment=False,
                download_name=f'example_{cache_key}.mp3'
            )
        elif resp.status_code == 429:
            return jsonify({
                'error': 'TTS quota exceeded. Please try again later.',
                'quota_reset': 'Check your MiniMax dashboard'
            }), 429
        else:
            return jsonify({'error': f'TTS failed: {resp.text}'}), resp.status_code

    except requests.exceptions.Timeout:
        return jsonify({'error': 'TTS request timeout'}), 504
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'TTS error: {str(e)}'}), 500


# ── Batch generation (admin) ────────────────────────────────────────────────────

_generating_books: set = set()  # 正在生成的 book_id 集合


def _get_book_examples(book_id):
    """返回词书中所有有例句的单词及例句."""
    from routes.books import load_book_vocabulary
    words = load_book_vocabulary(book_id)
    result = []
    for w in words:
        examples = w.get('examples', [])
        if examples:
            result.append({'word': w['word'], 'sentence': examples[0]['en']})
    return result


def _cache_file_path(sentence: str, voice_id: str) -> Path:
    """Return cache file path for (sentence, voice_id)."""
    import hashlib
    key = hashlib.md5(f"ex:{sentence}:{voice_id}".encode()).hexdigest()[:16]
    return _cache_dir() / f'{key}.mp3'


def _count_cached(book_id: str, examples: list) -> int:
    """返回已缓存的句子数（两个 voice 任一存在即算已缓存）."""
    cached = 0
    for ex in examples:
        sentence = ex['sentence']
        for vid in _ALTERNATING_VOICES:
            if _cache_file_path(sentence, vid).exists():
                cached += 1
                break
    return cached


def _generate_for_book(book_id: str, examples: list):
    """后台批量生成任务（eventlet spawn）."""
    global _generating_books
    try:
        for ex in examples:
            sentence = ex['sentence']
            for voice_id in _ALTERNATING_VOICES:
                cache_path = _cache_file_path(sentence, voice_id)
                if cache_path.exists():
                    continue
                try:
                    _call_tts_api(sentence, voice_id, cache_path)
                except Exception as e:
                    print(f'[TTS Gen Error] {sentence[:30]}: {e}')
                eventlet.sleep(0.2)
    finally:
        _generating_books.discard(book_id)


def _call_tts_api(sentence: str, voice_id: str, save_path: Path):
    """调用 MiniMax TTS 并保存到 save_path."""
    import requests
    api_key = _get_api_key()
    url = f"{MINIMAX_BASE_URL}/v1/t2a_v2"
    sentence_with_pauses = add_pause_tags(sentence, pause_seconds=0.4)
    payload = {
        "model": "speech-2.8-hd",
        "text": sentence_with_pauses,
        "stream": False,
        "voice_setting": {
            "voice_id": voice_id,
            "speed": 0.9,
            "vol": 1.0,
            "pitch": 0,
            "emotion": "neutral"
        },
        "audio_setting": {
            "sample_rate": 32000,
            "bitrate": 128000,
            "format": "mp3",
            "channel": 1
        }
    }
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    if resp.status_code != 200:
        raise Exception(f"TTS API error: {resp.status_code}")
    resp_data = resp.json()
    audio_hex = resp_data.get('data', {}).get('audio')
    if not audio_hex:
        raise Exception("No audio in response")
    audio_bytes = bytes.fromhex(audio_hex)
    with open(save_path, 'wb') as f:
        f.write(audio_bytes)


@tts_bp.route('/admin/books-summary', methods=['GET'])
@admin_required
def admin_books_summary():
    """所有词书 TTS 进度摘要."""
    from routes.books import VOCAB_BOOKS
    result = []
    for book in VOCAB_BOOKS:
        examples = _get_book_examples(book['id'])
        total = len(examples)
        cached = _count_cached(book['id'], examples)
        result.append({
            'book_id': book['id'],
            'title': book['title'],
            'total': total,
            'cached': cached,
        })
    return jsonify({'books': result}), 200


@tts_bp.route('/admin/generate/<book_id>', methods=['POST'])
@admin_required
def admin_generate_book(book_id):
    """触发后台生成任务."""
    from routes.books import VOCAB_BOOKS
    if not any(b['id'] == book_id for b in VOCAB_BOOKS):
        return jsonify({'error': 'Book not found'}), 404
    examples = _get_book_examples(book_id)
    if not examples:
        return jsonify({'error': 'No examples found'}), 400
    if book_id in _generating_books:
        return jsonify({'error': 'Already generating', 'total': len(examples)}), 409
    _generating_books.add(book_id)
    total = len(examples)
    eventlet.spawn(_generate_for_book, book_id, examples)
    return jsonify({'message': 'Generation started', 'total': total}), 202


@tts_bp.route('/admin/status/<book_id>', methods=['GET'])
@admin_required
def admin_tts_status(book_id):
    """查询单个词书进度."""
    examples = _get_book_examples(book_id)
    total = len(examples)
    cached = _count_cached(book_id, examples)
    generating = book_id in _generating_books
    return jsonify({
        'book_id': book_id,
        'total': total,
        'cached': cached,
        'generating': generating,
    }), 200
