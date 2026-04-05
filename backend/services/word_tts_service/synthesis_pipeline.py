class _PerModelScheduler:
    def __init__(self):
        self._lock = threading.Lock()
        self._next_allowed_at: dict[str, float] = {}
        self._cooldown_until: dict[str, float] = {}
        self._disabled: dict[str, str] = {}

    def acquire(self, models: list[str]) -> str:
        while True:
            with self._lock:
                active = [m for m in models if m not in self._disabled]
                if not active:
                    raise RuntimeError(f'No available TTS models remain in pool: {self._disabled}')

                now = time.monotonic()
                ranked: list[tuple[float, str]] = []
                for model in active:
                    ready_at = max(
                        self._next_allowed_at.get(model, 0.0),
                        self._cooldown_until.get(model, 0.0),
                    )
                    ranked.append((ready_at, model))
                ranked.sort(key=lambda item: (item[0], _model_rate_interval(item[1]), item[1]))
                ready_at, chosen = ranked[0]
                if ready_at <= now:
                    self._next_allowed_at[chosen] = now + _model_rate_interval(chosen)
                    return chosen
                sleep_for = ready_at - now
            time.sleep(min(sleep_for, 0.5))

    def cooldown(self, model: str, delay: float) -> None:
        if delay <= 0.0:
            return
        with self._lock:
            now = time.monotonic()
            self._cooldown_until[model] = max(
                self._cooldown_until.get(model, 0.0),
                now + delay,
            )

    def disable(self, model: str, reason: str) -> None:
        with self._lock:
            if model not in self._disabled:
                self._disabled[model] = reason
                print(f'[TTS Model Disabled] {model}: {reason}')

    def reserve_single(self, model: str) -> None:
        interval = _model_rate_interval(model)
        if interval <= 0.0:
            return
        while True:
            with self._lock:
                now = time.monotonic()
                ready_at = max(
                    self._next_allowed_at.get(model, 0.0),
                    self._cooldown_until.get(model, 0.0),
                )
                if ready_at <= now:
                    self._next_allowed_at[model] = now + interval
                    return
                sleep_for = ready_at - now
            time.sleep(min(sleep_for, 0.5))


_MODEL_SCHEDULER = _PerModelScheduler()


def _next_model() -> str:
    global _model_idx
    with _model_lock:
        m = MODELS[_model_idx % len(MODELS)]
        _model_idx += 1
        return m


def synthesize_word_to_bytes(
    text: str,
    model: str | None = None,
    voice: str | None = None,
    provider: str | None = None,
) -> bytes:
    """
    Call MiniMax, CosyVoice or Qwen HTTP REST API and return MP3 bytes.
    Automatically dispatches based on _TTS_PROVIDER setting.
    Raises on any API failure.
    """
    import requests

    resolved_provider = (provider or _TTS_PROVIDER).strip().lower()

    if resolved_provider == 'hybrid':
        dictionary_audio = fetch_dictionary_word_audio_bytes(text)
        if dictionary_audio is not None:
            return dictionary_audio

        fallback_provider = 'minimax' if _MINIMAX_API_KEYS else _TTS_PROVIDER
        fallback_model = _strip_word_tts_strategy_tag(model)
        fallback_voice = (
            (voice or '').strip()
            or (_MINIMAX_VOICE if fallback_provider == 'minimax' else DEFAULT_VOICE)
        )
        return synthesize_word_to_bytes(
            text,
            fallback_model,
            fallback_voice,
            provider=fallback_provider,
        )

    # ── MiniMax (fastest: direct hex in response, no second request) ───────────
    if resolved_provider == 'minimax':
        # Try voices in order; 2054 triggers fallback to next voice
        voices_to_try = _MINIMAX_FALLBACK_VOICES
        last_error: Exception | None = None
        requested_model = (model or _MINIMAX_DEFAULT_MODEL).strip() or _MINIMAX_DEFAULT_MODEL
        for attempt_voice_idx in range(len(voices_to_try)):
            minimax_key, per_key_sem, global_sem, key_voice = _get_minimax_key_with_sem()
            try:
                # Pick voice: primary → fallback based on 2054 history
                if attempt_voice_idx == 0:
                    chosen_voice = voice or key_voice
                else:
                    chosen_voice = voices_to_try[attempt_voice_idx]

                payload = {
                    'model': requested_model,
                    'text': text,
                    'stream': False,
                    'voice_setting': {
                        'voice_id': chosen_voice,
                        'speed': _MINIMAX_SPEED,
                        'vol': 1.0,
                        'pitch': 0,
                        'emotion': 'neutral',
                    },
                    'audio_setting': {
                        'sample_rate': 32000,
                        'bitrate': 128000,
                        'format': 'mp3',
                        'channel': 1,
                    },
                }
                headers = {
                    'Authorization': f'Bearer {minimax_key}',
                    'Content-Type': 'application/json',
                }
                resp = requests.post(
                    f'{_MINIMAX_BASE_URL}/v1/t2a_v2',
                    headers=headers,
                    json=payload,
                    timeout=30,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    base = data.get('base_resp', {})
                    status_code = int(base.get('status_code', 0))
                    if status_code == 0:
                        audio_hex = data.get('data', {}).get('audio')
                        if not audio_hex:
                            raise RuntimeError('MiniMax TTS: no audio in response')
                        return bytes.fromhex(audio_hex)
                    elif status_code == 2054 and attempt_voice_idx < len(voices_to_try) - 1:
                        # 2054 with this voice → try next fallback voice
                        continue
                    else:
                        raise DashScopeHTTPError(
                            f"MiniMax error {status_code}: {base.get('status_msg', '')}",
                            status_code,
                        )
                elif resp.status_code == 429:
                    raise DashScopeHTTPError('MiniMax 429 rate limit', 429)
                else:
                    raise DashScopeHTTPError(
                        f'MiniMax HTTP {resp.status_code}: {resp.text[:200]}',
                        resp.status_code,
                    )
            except DashScopeHTTPError as e:
                last_error = e
                # Only retry 429/rate-limit; permanent errors break immediately
                if e.status_code not in (429, 1002):
                    raise
                if attempt_voice_idx < len(voices_to_try) - 1:
                    continue
                raise
            except Exception as e:
                last_error = e
                raise
            finally:
                per_key_sem.release()
                global_sem.release()
        if last_error:
            raise last_error

    requested_model = (model or DEFAULT_MODEL).strip()
    requested_voice = (voice or DEFAULT_VOICE).strip()
    api_key = _get_api_key()
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
    }

    def do_request(actual_model: str, actual_voice: str) -> bytes:
        # ── CosyVoice family (character-based billing) ──────────────────────
        if actual_model.startswith('cosyvoice') or actual_model.startswith('sambert'):
            payload = {
                'model': actual_model,
                'input': {
                    'text': text,
                    'voice': actual_voice,
                    'format': 'mp3',
                    'sample_rate': 24000,
                },
            }
            resp = requests.post(
                _COSYVOICE_HTTP_URL,
                headers=headers,
                json=payload,
                timeout=30,
            )
            if resp.status_code == 200:
                data = resp.json()
                audio_data = data.get('output', {}).get('audio', {})
                b64 = audio_data.get('data')
                if b64:
                    import base64
                    return ensure_mp3_bytes(base64.b64decode(b64))
                url = audio_data.get('url')
                if url:
                    audio_resp = requests.get(url, timeout=30)
                    if audio_resp.ok:
                        return ensure_mp3_bytes(audio_resp.content)
                raise RuntimeError(f'CosyVoice response missing audio: {audio_data}')
            if resp.status_code == 429:
                raise DashScopeHTTPError(f'{actual_model} 429 rate limit exceeded', 429)
            raise DashScopeHTTPError(
                f'DashScope CosyVoice HTTP {resp.status_code}: {resp.text[:300]}',
                resp.status_code,
            )

        # ── Qwen TTS family (token-based billing) ────────────────────────────
        payload = {
            'model': actual_model,
            'input': {
                'text': text,
                'voice': actual_voice,
                'language_type': 'English',
            },
        }
        resp = requests.post(
            _QWEN_HTTP_URL,
            headers=headers,
            json=payload,
            timeout=30,
        )
        if resp.status_code == 200:
            data = resp.json()
            status = data.get('status_code')
            if status and status != 200:
                code = data.get('code', '')
                msg = data.get('message', '')
                raise DashScopeHTTPError(
                    f'{actual_model} error {code}: {msg}',
                    int(status),
                )
            audio_data = data.get('output', {}).get('audio', {})
            b64 = audio_data.get('data')
            if b64:
                import base64
                return ensure_mp3_bytes(base64.b64decode(b64))
            url = audio_data.get('url')
            if url:
                audio_resp = requests.get(url, timeout=30)
                if audio_resp.ok:
                    return ensure_mp3_bytes(audio_resp.content)
            raise RuntimeError(f'Qwen TTS response missing audio: {audio_data}')
        if resp.status_code == 429:
            raise DashScopeHTTPError(f'{actual_model} 429 rate limit exceeded', 429)
        raise DashScopeHTTPError(
            f'Qwen TTS HTTP {resp.status_code}: {resp.text[:300]}',
            resp.status_code,
        )

    if _should_use_generation_pool(requested_model, provider=resolved_provider):
        last_error: Exception | None = None
        attempts = max(1, len(MODELS) * 2)
        for _ in range(attempts):
            actual_model = _MODEL_SCHEDULER.acquire(MODELS)
            try:
                return do_request(actual_model, requested_voice)
            except Exception as exc:
                last_error = exc
                if _is_rate_limit_error(exc):
                    _MODEL_SCHEDULER.cooldown(actual_model, max(1.0, _model_rate_interval(actual_model) * 2.0))
                    continue
                if _is_permanent_model_error(exc):
                    _MODEL_SCHEDULER.disable(actual_model, str(exc)[:200])
                    continue
                raise
        if last_error:
            raise last_error
        raise RuntimeError('No TTS model succeeded in generation pool')

    _MODEL_SCHEDULER.reserve_single(requested_model)
    return do_request(requested_model, requested_voice)


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
