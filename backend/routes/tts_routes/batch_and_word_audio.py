def _call_tts_api(sentence: str, voice_id: str, save_path: Path):
    """调用当前 TTS provider 并保存到 save_path，遇到 429 时做退避重试。"""
    from services.word_tts import _is_rate_limit_error, synthesize_word_to_bytes

    provider = _current_tts_provider()
    model, _ = default_cache_identity()
    text_for_tts = add_pause_tags(sentence, pause_seconds=0.4) if provider == 'minimax' else sentence
    backoff_delays = [10, 20, 40] if provider == 'azure' else [30, 60, 120]

    for attempt in range(len(backoff_delays) + 1):
        try:
            audio_bytes = synthesize_word_to_bytes(
                text_for_tts,
                model,
                voice_id,
                provider=provider,
                content_mode='sentence' if provider == 'azure' else None,
            )
            write_bytes_atomically(save_path, audio_bytes)
            return
        except Exception as exc:
            if _is_rate_limit_error(exc) and attempt < len(backoff_delays):
                delay = backoff_delays[attempt]
                print(
                    f'[TTS 429] 退避 {delay}s '
                    f'(第{attempt + 1}次重试, provider={provider}, voice={voice_id})'
                )
                runtime_sleep(delay)
                continue
            raise


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


tts_admin_bp = Blueprint('tts_admin_legacy', __name__)


@tts_admin_bp.route('/books-summary', methods=['GET'])
@admin_required
def admin_books_summary(current_user):
    """所有词书 TTS 进度摘要."""
    from services.books_registry_service import VOCAB_BOOKS
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


@tts_admin_bp.route('/generate/<book_id>', methods=['POST'])
@admin_required
def admin_generate_book(current_user, book_id):
    """触发后台生成任务（interrupted/error 状态可重新触发）."""
    from services.books_registry_service import VOCAB_BOOKS
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


@tts_admin_bp.route('/status/<book_id>', methods=['GET'])
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
_AUDIO_OSS_URL_HEADER = 'X-Audio-Oss-Url'
_AUDIO_SOURCE_HEADER = 'X-Audio-Source'
_CURRENT_WORD_CACHE_TAG = 'azure-word-v6-ielts-rp-female-onset-buffer'
_SEGMENTED_WORD_CACHE_TAG = 'azure-word-segmented-v1'
_LEGACY_WORD_CACHE_TAG = 'azure-word-v5-ielts-rp-female-onset-buffer'
_LEGACY_NORMAL_WORD_VOICES = (
    'en-GB-LibbyNeural',
)
_LEGACY_SEGMENTED_WORD_VOICES = (
    'en-GB-LibbyNeural',
)


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
    """eventlet: 批量生成单词 MP3。"""
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


def _normalize_word_audio_pronunciation_mode(value: str | None) -> str:
    normalized = (value or '').strip().lower()
    if normalized in {'word-segmented', 'phonetic-segments', 'phonetic_segments'}:
        return 'word-segmented'
    return 'word'


def _resolve_normal_word_audio_identity() -> tuple[str, str, str]:
    from services.word_tts import azure_default_model, azure_word_voice

    return (
        'azure',
        f'{azure_default_model()}@{_CURRENT_WORD_CACHE_TAG}',
        azure_word_voice(),
    )


def _resolve_word_audio_identity(pronunciation_mode: str) -> tuple[str, str, str, str]:
    if pronunciation_mode == 'word-segmented':
        from services.word_tts import azure_default_model, azure_word_voice

        return (
            'azure',
            f'{azure_default_model()}@{_SEGMENTED_WORD_CACHE_TAG}',
            azure_word_voice(),
            'word-segmented',
        )

    provider, model, voice = _resolve_normal_word_audio_identity()
    return provider, model, voice, 'word'


def _resolve_word_audio_identity_candidates(
    pronunciation_mode: str,
) -> list[tuple[str, str, str, str]]:
    primary = _resolve_word_audio_identity(pronunciation_mode)
    provider, model, voice, content_mode = primary
    candidates: list[tuple[str, str, str, str]] = []
    seen: set[tuple[str, str, str, str]] = set()

    def append_candidate(candidate_model: str, candidate_voice: str):
        candidate = (provider, candidate_model, candidate_voice, content_mode)
        if candidate in seen:
            return
        seen.add(candidate)
        candidates.append(candidate)

    append_candidate(model, voice)
    if pronunciation_mode != 'word-segmented':
        if provider != 'azure':
            return candidates
        base_model, separator, _cache_tag = model.partition('@')
        if not separator:
            return candidates
        legacy_model = f'{base_model}@{_LEGACY_WORD_CACHE_TAG}'
        append_candidate(legacy_model, voice)
        for fallback_voice in _LEGACY_NORMAL_WORD_VOICES:
            normalized_voice = (fallback_voice or '').strip()
            if not normalized_voice:
                continue
            append_candidate(legacy_model, normalized_voice)
        return candidates

    for fallback_voice in _LEGACY_SEGMENTED_WORD_VOICES:
        normalized_voice = (fallback_voice or '').strip()
        if not normalized_voice:
            continue
        append_candidate(model, normalized_voice)
    return candidates


@tts_bp.route('/word-audio', methods=['GET'])
def get_word_audio():
    """
    返回单词读音 MP3。
    若本地缓存缺失，则优先抓取词典录音，拿不到再同步调用 TTS 生成。
    Query: w — 单词文本（最长 160 字符）
    """
    from services.word_tts import (
        _strip_word_tts_strategy_tag,
        normalize_word_key,
        synthesize_word_to_bytes,
        word_tts_cache_path,
    )
    from services.word_tts_oss import (
        fetch_word_audio_oss_payload,
        resolve_word_audio_oss_metadata,
    )

    raw = (request.args.get('w') or '').strip()
    if not raw or len(raw) > 160:
        return jsonify({'error': 'invalid w'}), 400
    cache_only = request.args.get('cache_only') == '1' or request.headers.get('X-Audio-Cache-Only') == '1'
    pronunciation_mode = _normalize_word_audio_pronunciation_mode(request.args.get('pronunciation_mode'))
    phonetic = (request.args.get('phonetic') or '').strip()
    if not phonetic or phonetic == '/暂无音标/':
        phonetic = None

    key = normalize_word_key(raw)
    identity_candidates = _resolve_word_audio_identity_candidates(pronunciation_mode)
    provider, model, voice, content_mode = identity_candidates[0]
    cache_dir = _word_tts_dir()
    path = word_tts_cache_path(cache_dir, key, model, voice)
    if request.method == 'HEAD':
        for _candidate_provider, candidate_model, candidate_voice, _candidate_content_mode in identity_candidates:
            candidate_path = word_tts_cache_path(cache_dir, key, candidate_model, candidate_voice)
            if candidate_path.exists() and not is_probably_valid_mp3_file(candidate_path):
                remove_invalid_cached_audio(candidate_path)
            oss_metadata = resolve_word_audio_oss_metadata(
                file_name=candidate_path.name,
                model=candidate_model,
                voice=candidate_voice,
            )
            if oss_metadata is not None:
                response = _audio_metadata_response(
                    oss_metadata.byte_length,
                    cache_key=oss_metadata.cache_key,
                )
                response.headers[_AUDIO_OSS_URL_HEADER] = oss_metadata.signed_url
                response.headers[_AUDIO_SOURCE_HEADER] = 'oss'
                return response
            if candidate_path.exists():
                response = _audio_metadata_response(
                    candidate_path.stat().st_size,
                    cache_key=_audio_cache_key(candidate_path),
                )
                response.headers[_AUDIO_SOURCE_HEADER] = 'local'
                return response
        response = _audio_metadata_response(None, cache_key=None)
        response.headers[_AUDIO_SOURCE_HEADER] = 'missing'
        return response
    for _candidate_provider, candidate_model, candidate_voice, _candidate_content_mode in identity_candidates:
        candidate_path = word_tts_cache_path(cache_dir, key, candidate_model, candidate_voice)
        if candidate_path.exists() and not is_probably_valid_mp3_file(candidate_path):
            remove_invalid_cached_audio(candidate_path)
        oss_metadata = resolve_word_audio_oss_metadata(
            file_name=candidate_path.name,
            model=candidate_model,
            voice=candidate_voice,
        )
        if oss_metadata is not None:
            oss_payload = fetch_word_audio_oss_payload(
                file_name=candidate_path.name,
                model=candidate_model,
                voice=candidate_voice,
            )
            if oss_payload is not None:
                response = Response(oss_payload.audio_bytes, mimetype=oss_payload.content_type or 'audio/mpeg')
                response = _apply_audio_headers(
                    response,
                    byte_length=oss_payload.byte_length,
                    cache_key=oss_payload.cache_key,
                )
                response.headers[_AUDIO_OSS_URL_HEADER] = oss_payload.signed_url
                response.headers[_AUDIO_SOURCE_HEADER] = 'oss'
                return response
        if candidate_path.exists():
            response = send_file(
                candidate_path,
                mimetype='audio/mpeg',
                as_attachment=False,
                download_name=f'{key}.mp3',
                conditional=False,
            )
            response = _apply_audio_headers(
                response,
                byte_length=candidate_path.stat().st_size,
                cache_key=_audio_cache_key(candidate_path),
            )
            if oss_metadata is not None:
                response.headers[_AUDIO_OSS_URL_HEADER] = oss_metadata.signed_url
            response.headers[_AUDIO_SOURCE_HEADER] = 'local'
            return response

    if not path.exists():
        if cache_only:
            return jsonify({'error': 'word audio cache miss'}), 404
        try:
            synthesis_model = _strip_word_tts_strategy_tag(model)
            audio_bytes = synthesize_word_to_bytes(
                raw,
                synthesis_model,
                voice,
                provider=provider,
                content_mode=content_mode,
                phonetic=phonetic if content_mode == 'word-segmented' else None,
            )
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
        conditional=False,
    )
    response = _apply_audio_headers(
        response,
        byte_length=path.stat().st_size,
        cache_key=_audio_cache_key(path),
    )
    response.headers[_AUDIO_SOURCE_HEADER] = 'local'
    return response


@tts_admin_bp.route('/admin/generate-words', methods=['POST'])
@admin_required
def admin_generate_words(current_user):
    """
    后台批量生成所有词书单词的 TTS（去重）。
    Body 可选: { "book_id": "ielts_ultimate" } 限制单本书；省略则全词书。
    """
    global _generating_words
    from services.books_registry_service import VOCAB_BOOKS

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


@tts_admin_bp.route('/admin/word-audio-status', methods=['GET'])
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
    _, model, voice = _resolve_normal_word_audio_identity()
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
