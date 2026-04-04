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
                runtime_sleep(delay)
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
    spawn_background(_generate_for_book, book_id, examples)
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


# ── MiniMax 单词离线 TTS ───────────────────────────────────────────────────────

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
    """eventlet: 批量生成单词 MP3（MiniMax）."""
    global _generating_words
    from services.word_tts import run_batch_generate_missing

    cache_dir = _word_tts_dir()

    try:
        run_batch_generate_missing(
            book_ids,
            cache_dir=cache_dir,
            sleep_fn=runtime_sleep,
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
    返回单词读音 MP3。
    若本地缓存缺失，则优先抓取词典录音，拿不到再同步调用 TTS 生成。
    Query: w — 单词文本（最长 160 字符）
    """
    from services.word_tts import (
        normalize_word_key,
        synthesize_word_to_bytes,
        word_tts_cache_path,
    )

    raw = (request.args.get('w') or '').strip()
    if not raw or len(raw) > 160:
        return jsonify({'error': 'invalid w'}), 400

    key = normalize_word_key(raw)
    provider, model, voice = default_word_tts_identity()
    path = word_tts_cache_path(_word_tts_dir(), key, model, voice)
    if path.exists() and not is_probably_valid_mp3_file(path):
        remove_invalid_cached_audio(path)
    if not path.exists():
        try:
            audio_bytes = synthesize_word_to_bytes(raw, model, voice, provider=provider)
            write_bytes_atomically(path, audio_bytes)
        except Exception as exc:
            current_app.logger.exception('Word audio generation failed for "%s"', raw)
            status_code = getattr(exc, 'status_code', 502)
            if not isinstance(status_code, int) or status_code < 400 or status_code >= 600:
                status_code = 502
            return jsonify({'error': 'word audio generation failed'}), status_code

    response = send_file(
        path,
        mimetype='audio/mpeg',
        as_attachment=False,
        download_name=f'{key}.mp3',
    )
    response.headers['Cache-Control'] = 'no-store, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    return response


@tts_bp.route('/admin/generate-words', methods=['POST'])
@admin_required
def admin_generate_words(current_user):
    """
    后台批量生成所有词书单词的 MiniMax TTS（去重）。
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
    spawn_background(_generate_words_worker, book_ids)
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
