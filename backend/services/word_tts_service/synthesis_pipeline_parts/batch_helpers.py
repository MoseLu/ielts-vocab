def collect_unique_words(book_ids: list[str] | None = None) -> list[str]:
    """
    All distinct words from VOCAB_BOOKS (or subset), first-seen casing preserved.
    Sorted case-insensitively for stable batch order.
    """
    from routes.books import VOCAB_BOOKS, load_book_vocabulary

    seen_set: set[str] = set()
    out: list[str] = []

    books = (
        VOCAB_BOOKS
        if book_ids is None
        else [b for b in VOCAB_BOOKS if b['id'] in book_ids]
    )
    for book in books:
        vocab = load_book_vocabulary(book['id'])
        if not vocab:
            continue
        for entry in vocab:
            w = (entry.get('word') or '').strip()
            if not w:
                continue
            k = w.lower()
            if k in seen_set:
                continue
            seen_set.add(k)
            out.append(w)

    out.sort(key=str.lower)
    return out


def word_tts_data_dir() -> Path:
    """backend/word_tts_cache — same path as routes.tts._word_tts_dir()."""
    d = Path(__file__).resolve().parent.parent / 'word_tts_cache'
    d.mkdir(parents=True, exist_ok=True)
    return d


def count_cached_words(
    words: list[str],
    cache_dir: Path,
    model: str,
    voice: str,
) -> int:
    n = 0
    for w in words:
        key = normalize_word_key(w)
        if not key:
            continue
        if word_tts_cache_path(cache_dir, key, model, voice).exists():
            n += 1
    return n


def write_batch_progress(
    cache_dir: Path,
    total: int,
    completed: int,
    status: str,
    *,
    current_word: str | None = None,
) -> None:
    payload: dict = {
        'total': total,
        'completed': completed,
        'status': status,
        'updated_at': datetime.utcnow().isoformat(),
    }
    if current_word is not None:
        payload['current_word'] = current_word
    p = cache_dir / 'progress_all_words.json'
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')


class DashScopeHTTPError(Exception):
    """Carries the HTTP status code so callers can distinguish 429 from transient errors."""

    def __init__(self, message: str, status_code: int):
        super().__init__(message)
        self.status_code = status_code


def _is_rate_limit_error(exc: Exception) -> bool:
    """Return True for transient errors that should be retried (429, 1002=RPM).
    2054=voice_id_not_exist is permanent and should NOT be retried."""
    msg = str(exc)
    # Explicit DashScope HTTP 429
    if isinstance(exc, DashScopeHTTPError) and exc.status_code == 429:
        return True
    # MiniMax RPM limit — transient, retry
    if isinstance(exc, DashScopeHTTPError) and exc.status_code == 1002:
        return True
    # WebSocket JSON errors from DashScope (Throttling.RateQuota, etc.)
    if 'Throttling' in msg or 'RateQuota' in msg:
        return True
    # Explicit "rate quota exceeded" text
    if 'rate quota' in msg.lower():
        return True
    return False


def recommended_batch_rate_interval(
    model: str | None = None,
    *,
    provider: str | None = None,
) -> float:
    resolved_provider = (provider or _TTS_PROVIDER).strip().lower()
    resolved_model = (model or DEFAULT_MODEL).strip().lower()
    if resolved_provider != 'minimax' and _should_use_generation_pool(
        model or DEFAULT_MODEL,
        provider=resolved_provider,
    ):
        return 0.0
    if resolved_provider == 'dashscope' and resolved_model in {
        'qwen-tts-2025-05-22',
        'qwen-tts-latest',
        'qwen-tts-2025-04-10',
        'qwen-tts',
    }:
        # Official RPM is low enough that we need a strict global interval.
        return 7.0
    return 0.0
