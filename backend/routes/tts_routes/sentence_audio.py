"""
MiniMax TTS (Text-to-Speech) 路由
使用 MiniMax Speech-01 系列模型生成高质量英语例句音频
本地缓存：相同 sentence + voice 只调用一次 API，之后直接读文件
"""

import os
import io
import json
import hashlib
import requests
from datetime import datetime
from pathlib import Path
from flask import Blueprint, request, jsonify, send_file, current_app
from dotenv import load_dotenv
from routes.middleware import admin_required
from services.runtime_async import sleep as runtime_sleep, spawn_background
from services.word_tts import (
    default_cache_identity,
    default_word_tts_identity,
    is_probably_valid_mp3_bytes,
    is_probably_valid_mp3_file,
    remove_invalid_cached_audio,
    write_bytes_atomically,
)

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

# Example audio voice pool. Selection is deterministic per sentence so
# repeated requests stay stable under retries and concurrency.
_ALTERNATING_VOICES = ['English_Trustworthy_Man', 'Serene_Woman']


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


def _select_voice_for_sentence(sentence: str) -> str:
    digest = hashlib.md5(sentence.encode('utf-8')).digest()
    return _ALTERNATING_VOICES[digest[0] % len(_ALTERNATING_VOICES)]


def _current_tts_provider() -> str:
    return os.environ.get('BAILIAN_TTS_PROVIDER', 'minimax').strip().lower()


def _example_tts_identity(sentence: str) -> tuple[str, str]:
    model, voice = default_cache_identity()
    if _current_tts_provider() == 'minimax':
        return model, _select_voice_for_sentence(sentence)
    return model, voice


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
    if cached.exists() and is_probably_valid_mp3_file(cached):
        return send_file(cached, mimetype='audio/mpeg', as_attachment=False,
                        download_name=f'tts_{cache_key}.mp3')
    remove_invalid_cached_audio(cached)

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
            resp_data = resp.json()
            audio_hex = resp_data.get('data', {}).get('audio')
            if not audio_hex:
                return jsonify({'error': 'No audio in response', 'response': resp_data}), 500
            audio_bytes = bytes.fromhex(audio_hex)
            if not is_probably_valid_mp3_bytes(audio_bytes):
                return jsonify({'error': 'Invalid MP3 payload returned by TTS provider'}), 502
            write_bytes_atomically(cached, audio_bytes)
            audio_data = io.BytesIO(audio_bytes)
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
    if not sentence:
        return jsonify({'error': 'sentence is required'}), 400

    from services.word_tts import synthesize_word_to_bytes

    provider = _current_tts_provider()
    model, voice_id = _example_tts_identity(sentence)
    text_for_tts = (
        add_pause_tags(sentence, pause_seconds=0.4)
        if provider == 'minimax'
        else sentence
    )

    # 缓存路径包含 model，避免 provider/model 切换时命中错误的旧文件
    cache_key = hashlib.md5(f"ex:{sentence}:{model}:{voice_id}".encode()).hexdigest()[:16]
    cached_file = _cache_dir() / f'{cache_key}.mp3'

    # 命中缓存 → 直接返回本地文件
    if cached_file.exists() and is_probably_valid_mp3_file(cached_file):
        print(f"[TTS Cache HIT] {cached_file.name} (voice={voice_id})")
        return send_file(cached_file, mimetype='audio/mpeg', as_attachment=False,
                        download_name=f'example_{cache_key}.mp3')
    remove_invalid_cached_audio(cached_file)

    print(
        f"[TTS Cache MISS] provider={provider} model={model} "
        f"voice={voice_id}, sentence={sentence[:60]}..."
    )

    try:
        audio_bytes = synthesize_word_to_bytes(text_for_tts, model, voice_id)
        write_bytes_atomically(cached_file, audio_bytes)
        print(f"[TTS Cache SAVED] {cached_file.name} ({len(audio_bytes)} bytes)")

        audio_data = io.BytesIO(audio_bytes)
        audio_data.seek(0)
        return send_file(
            audio_data,
            mimetype='audio/mpeg',
            as_attachment=False,
            download_name=f'example_{cache_key}.mp3'
        )
    except Exception as exc:
        current_app.logger.exception('Example audio generation failed for "%s"', sentence)
        status_code = getattr(exc, 'status_code', 502)
        if not isinstance(status_code, int) or status_code < 400 or status_code >= 600:
            status_code = 502
        return jsonify({'error': 'TTS failed'}), status_code


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


# ── Progress persistence ──────────────────────────────────────────────────────

def _progress_file(book_id: str) -> Path:
    return _cache_dir() / f'progress_{book_id}.json'


def _read_progress(book_id: str) -> dict | None:
    p = _progress_file(book_id)
    if not p.exists():
        return None
    try:
        import json
        return json.loads(p.read_text())
    except Exception:
        return None


def _write_progress(book_id: str, total: int, completed: int, status: str):
    import json
    from datetime import datetime
    _progress_file(book_id).write_text(json.dumps({
        'total': total,
        'completed': completed,
        'status': status,
        'updated_at': datetime.utcnow().isoformat(),
    }))


def _generate_for_book(book_id: str, examples: list):
    """后台批量生成任务（eventlet spawn）。
    - 遇到 429 时通过 _call_tts_api 自动退避重试
    - 每处理一条句子更新磁盘进度文件，重启后可继续查看进度
    """
    global _generating_books
    total = len(examples)
    completed = _count_cached(book_id, examples)
    _write_progress(book_id, total, completed, 'running')

    try:
        for ex in examples:
            sentence = ex['sentence']
            already_cached = any(_cache_file_path(sentence, v).exists() for v in _ALTERNATING_VOICES)
            if already_cached:
                continue

            for voice_id in _ALTERNATING_VOICES:
                cache_path = _cache_file_path(sentence, voice_id)
                if cache_path.exists():
                    continue
                try:
                    _call_tts_api(sentence, voice_id, cache_path)
                except Exception as e:
                    print(f'[TTS Gen Error] {sentence[:40]}: {e}')
                # 每次 API 调用后等待 1.5s，避免触发限速
                runtime_sleep(1.5)

            completed += 1
            # 每 5 条或最后一条时写入进度
            if completed % 5 == 0 or completed == total:
                _write_progress(book_id, total, completed, 'running')

        _write_progress(book_id, total, total, 'done')
    except Exception as e:
        print(f'[TTS Gen Fatal] book={book_id}: {e}')
        _write_progress(book_id, total, completed, 'error')
        raise
    finally:
        _generating_books.discard(book_id)
