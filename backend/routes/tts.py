"""
MiniMax TTS (Text-to-Speech) 路由
使用 MiniMax Speech-01 系列模型生成高质量英语例句音频
本地缓存：相同 sentence + voice 只调用一次 API，之后直接读文件
"""

import os
import io
import json
import hashlib
import eventlet
import requests
from datetime import datetime
from pathlib import Path
from flask import Blueprint, request, jsonify, send_file, current_app
from dotenv import load_dotenv
from routes.middleware import admin_required
from services.word_tts import (
    default_cache_identity,
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
    word = (data.get('word') or '').strip()

    if not sentence:
        return jsonify({'error': 'sentence is required'}), 400

    # 添加停顿标签，使句子有自然的节奏和停顿
    sentence_with_pauses = add_pause_tags(sentence, pause_seconds=0.4)

    # 交替使用两种语音
    voice_id = _select_voice_for_sentence(sentence)

    # 缓存路径：sentence + voice_id 作为 key
    cache_key = hashlib.md5(f"ex:{sentence}:{voice_id}".encode()).hexdigest()[:16]
    cached_file = _cache_dir() / f'{cache_key}.mp3'

    # 命中缓存 → 直接返回本地文件
    if cached_file.exists() and is_probably_valid_mp3_file(cached_file):
        print(f"[TTS Cache HIT] {cached_file.name} (voice={voice_id})")
        return send_file(cached_file, mimetype='audio/mpeg', as_attachment=False,
                        download_name=f'example_{cache_key}.mp3')
    remove_invalid_cached_audio(cached_file)

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
            if not is_probably_valid_mp3_bytes(audio_bytes):
                return jsonify({'error': 'Invalid MP3 payload returned by TTS provider'}), 502
            write_bytes_atomically(cached_file, audio_bytes)
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
                eventlet.sleep(1.5)

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


def _call_tts_api(sentence: str, voice_id: str, save_path: Path):
    """调用 MiniMax TTS 并保存到 save_path。
    遇到 429 先切换 API key，再指数退避重试（最多 3 次）。
    """
    import requests
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
    url = f"{MINIMAX_BASE_URL}/v1/t2a_v2"

    # 遇到 429 时的退避时长（秒）
    backoff_delays = [30, 60, 120]

    for attempt in range(len(backoff_delays) + 1):
        api_key = _get_api_key()
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=30)

        if resp.status_code == 200:
            resp_data = resp.json()
            audio_hex = resp_data.get('data', {}).get('audio')
            if not audio_hex:
                raise Exception("No audio in response")
            audio_bytes = bytes.fromhex(audio_hex)
            if not is_probably_valid_mp3_bytes(audio_bytes):
                raise Exception('Invalid MP3 payload returned by TTS provider')
            write_bytes_atomically(save_path, audio_bytes)
            return

        if resp.status_code == 429:
            if attempt < len(backoff_delays):
                delay = backoff_delays[attempt]
                print(f'[TTS 429] 退避 {delay}s (第{attempt + 1}次重试, voice={voice_id})')
                eventlet.sleep(delay)
                continue
            raise Exception(f"TTS 429: quota exceeded after {attempt + 1} attempts")

        raise Exception(f"TTS API error: {resp.status_code} {resp.text[:200]}")


def _book_status(book_id: str, generating: bool) -> str:
    """根据内存标志与进度文件推导当前状态字符串."""
    if generating:
        return 'running'
    progress = _read_progress(book_id)
    if progress is None:
        return 'idle'
    if progress['status'] == 'running':
        # 进度文件标记运行中但内存里不存在 → 服务重启导致中断
        return 'interrupted'
    return progress['status']  # 'done' | 'error' | 'idle'


@tts_bp.route('/books-summary', methods=['GET'])
@admin_required
def admin_books_summary(current_user):
    """所有词书 TTS 进度摘要."""
    from routes.books import VOCAB_BOOKS
    result = []
    for book in VOCAB_BOOKS:
        examples = _get_book_examples(book['id'])
        total = len(examples)
        cached = _count_cached(book['id'], examples)
        generating = book['id'] in _generating_books
        result.append({
            'book_id': book['id'],
            'title': book['title'],
            'color': book.get('color', '#3b82f6'),
            'total': total,
            'cached': cached,
            'generating': generating,
            'status': _book_status(book['id'], generating),
        })
    return jsonify({'books': result}), 200


@tts_bp.route('/generate/<book_id>', methods=['POST'])
@admin_required
def admin_generate_book(current_user, book_id):
    """触发后台生成任务（interrupted/error 状态可重新触发）."""
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


@tts_bp.route('/status/<book_id>', methods=['GET'])
@admin_required
def admin_tts_status(current_user, book_id):
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
        'status': _book_status(book_id, generating),
    }), 200


# ── DashScope (百炼) 单词离线 TTS ───────────────────────────────────────────────

_generating_words: bool = False


def _word_tts_dir() -> Path:
    d = Path(__file__).parent.parent / 'word_tts_cache'
    d.mkdir(exist_ok=True)
    return d


def _word_progress_file() -> Path:
    return _word_tts_dir() / 'progress_all_words.json'


def _read_word_progress() -> dict | None:
    p = _word_progress_file()
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding='utf-8'))
    except Exception:
        return None


def _write_word_progress(
    total: int,
    completed: int,
    status: str,
    *,
    current_word: str | None = None,
):
    payload = {
        'total': total,
        'completed': completed,
        'status': status,
        'updated_at': datetime.utcnow().isoformat(),
    }
    if current_word is not None:
        payload['current_word'] = current_word
    _word_progress_file().write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )


def _generate_words_worker(book_ids: list[str] | None):
    """eventlet: 批量生成单词 MP3（百炼 CosyVoice）."""
    global _generating_words
    from services.word_tts import run_batch_generate_missing

    cache_dir = _word_tts_dir()

    try:
        run_batch_generate_missing(
            book_ids,
            cache_dir=cache_dir,
            sleep_fn=eventlet.sleep,
        )
    except Exception as e:
        print(f'[Word TTS Fatal] {e}')
        prog = _read_word_progress()
        if prog:
            _write_word_progress(
                prog.get('total', 0),
                prog.get('completed', 0),
                'error',
                current_word=None,
            )
    finally:
        _generating_words = False


@tts_bp.route('/word-audio', methods=['GET'])
def get_word_audio():
    """
    返回已预生成的单词读音 MP3。未生成则 404，前端回退到 speechSynthesis。
    Query: w — 单词文本（最长 160 字符）
    """
    from services.word_tts import (
        word_tts_cache_path,
        normalize_word_key,
    )

    raw = (request.args.get('w') or '').strip()
    if not raw or len(raw) > 160:
        return jsonify({'error': 'invalid w'}), 400

    key = normalize_word_key(raw)
    model, voice = default_cache_identity()
    path = word_tts_cache_path(_word_tts_dir(), key, model, voice)
    if path.exists() and not is_probably_valid_mp3_file(path):
        remove_invalid_cached_audio(path)
    if not path.exists():
        return jsonify({'error': 'not generated'}), 404

    return send_file(
        path,
        mimetype='audio/mpeg',
        as_attachment=False,
        download_name=f'{key}.mp3',
    )


@tts_bp.route('/admin/generate-words', methods=['POST'])
@admin_required
def admin_generate_words(current_user):
    """
    后台批量生成所有词书单词的百炼 TTS（去重）。
    Body 可选: { "book_id": "ielts_ultimate" } 限制单本书；省略则全词书。
    """
    global _generating_words
    from routes.books import VOCAB_BOOKS

    data = request.get_json() or {}
    book_id = (data.get('book_id') or '').strip() or None

    if book_id:
        if not any(b['id'] == book_id for b in VOCAB_BOOKS):
            return jsonify({'error': 'Book not found'}), 404
        book_ids = [book_id]
    else:
        book_ids = None

    if _generating_words:
        return jsonify({'error': 'Already generating'}), 409

    from services.word_tts import collect_unique_words

    words = collect_unique_words(book_ids)
    if not words:
        return jsonify({'error': 'No words found'}), 400

    _generating_words = True
    eventlet.spawn(_generate_words_worker, book_ids)
    return jsonify({
        'message': 'Word TTS generation started',
        'total': len(words),
    }), 202


@tts_bp.route('/admin/word-audio-status', methods=['GET'])
@admin_required
def admin_word_audio_status(current_user):
    """单词离线 TTS 批量进度。"""
    from services.word_tts import (
        collect_unique_words,
        count_cached_words,
    )

    prog = _read_word_progress()
    words = collect_unique_words(None)
    total = len(words)
    model, voice = default_cache_identity()
    cached = count_cached_words(words, _word_tts_dir(), model, voice)

    status = 'idle'
    if _generating_words:
        status = 'running'
    elif prog:
        status = prog.get('status', 'idle')
        if status == 'running' and not _generating_words:
            status = 'interrupted'

    return jsonify({
        'total': total,
        'cached': cached,
        'generating': _generating_words,
        'status': status,
        'progress': prog,
    }), 200
