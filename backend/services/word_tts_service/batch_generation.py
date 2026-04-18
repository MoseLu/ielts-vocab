def recommended_batch_backoff_delays(rate_interval: float = 0.0) -> tuple[float, ...]:
    if _should_use_generation_pool(DEFAULT_MODEL):
        return (1.0, 2.0, 4.0)
    if rate_interval > 0:
        return (
            max(20.0, rate_interval * 3.0),
            max(40.0, rate_interval * 6.0),
            max(60.0, rate_interval * 9.0),
        )
    return (3.0, 6.0, 12.0)


def recommended_batch_concurrency(
    model: str | None = None,
    *,
    provider: str | None = None,
) -> int:
    resolved_model = model or DEFAULT_MODEL
    if _should_use_generation_pool(resolved_model, provider=provider):
        return max(8, min(16, len(MODELS) * 2))
    if recommended_batch_rate_interval(resolved_model, provider=provider) > 0:
        return 1
    return 16


class _RequestRateLimiter:
    def __init__(self, interval: float):
        self.interval = max(0.0, interval)
        self._lock = threading.Lock()
        self._next_allowed_at = 0.0

    def wait_for_turn(self) -> None:
        if self.interval <= 0.0:
            return
        while True:
            with self._lock:
                now = time.monotonic()
                if now >= self._next_allowed_at:
                    self._next_allowed_at = now + self.interval
                    return
                sleep_for = self._next_allowed_at - now
            time.sleep(min(sleep_for, 1.0))

    def cooldown(self, delay: float) -> None:
        if delay <= 0.0:
            return
        with self._lock:
            now = time.monotonic()
            self._next_allowed_at = max(self._next_allowed_at, now + delay)


def run_batch_generate_words(
    words: list[str],
    *,
    cache_dir: Path | None = None,
    provider: str | None = None,
    model: str | None = None,
    voice: str | None = None,
    content_mode: str = 'word',
    phonetic_lookup: Callable[[str], str] | None = None,
    concurrency: int = 6,
    backoff_delays: tuple[float, ...] | None = None,
    rate_interval: float = 0.0,
    sleep_fn: Callable[[float], None] | None = None,
    progress_callback: Callable[[dict], None] | None = None,
) -> dict:
    """
    Generate MP3 for the provided word list, skipping already valid cached audio.

    Concurrency: N worker threads call the API concurrently.  A token bucket
    refills at a fixed interval so the steady-state throughput is
    concurrency tokens per `rate_interval` seconds (e.g. 3/0.8 ≈ 3.75 req/s).

    On 429 / Throttling: all workers pause while one retries with exponential
    backoff; after backoff the token bucket resumes refilling normally.

    Returns stats dict with keys:
      total, completed_initial, completed_final, generated_this_run, errors.
    """
    if cache_dir is None:
        cache_dir = word_tts_data_dir()
    else:
        cache_dir.mkdir(parents=True, exist_ok=True)

    default_provider, default_model, default_voice = default_word_tts_identity()
    provider = (provider or default_provider).strip().lower()
    model = (model or default_model).strip() or default_model
    voice = (voice or default_voice).strip() or default_voice
    sleep = sleep_fn or time.sleep
    if rate_interval <= 0.0:
        rate_interval = recommended_batch_rate_interval(model, provider=provider)
    if backoff_delays is None:
        backoff_delays = recommended_batch_backoff_delays(rate_interval)
    concurrency = max(1, int(concurrency))
    if rate_interval > 0.0:
        concurrency = 1
    rate_limiter = _RequestRateLimiter(rate_interval)
    progress_every = 5 if rate_interval > 0.0 else 50
    words = [word for word in words if normalize_word_key(word)]
    total = len(words)
    completed = count_cached_words(words, cache_dir, model, voice)
    completed_initial = completed

    def emit_progress(status: str, current_word: str | None) -> None:
        if progress_callback is None:
            return
        progress_callback({
            'total': total,
            'completed_initial': completed_initial,
            'completed_final': completed,
            'generated_this_run': generated,
            'status': status,
            'current_word': current_word,
        })

    generated = 0
    emit_progress('running', None)

    if completed >= total:
        emit_progress('done', None)
        return {
            'total': total,
            'completed_initial': completed_initial,
            'completed_final': completed,
            'generated_this_run': 0,
            'errors': [],
        }

    # ── Concurrency: fixed-size semaphore (max concurrent API calls) ───────────
    sem = threading.Semaphore(concurrency)

    # ── Thread-safe counters ──────────────────────────────────────────────────
    completed_lock = threading.Lock()
    errors: list[str] = []
    errors_lock = threading.Lock()
    done_count = 0

    def process_word(w: str) -> bool:
        """Returns True if the word was newly generated, False if skipped."""
        key = normalize_word_key(w)
        if not key:
            return False
        out_path = word_tts_cache_path(cache_dir, key, model, voice)
        if out_path.exists() and is_probably_valid_mp3_file(out_path):
            return False
        remove_invalid_cached_audio(out_path)

        acquired = sem.acquire(blocking=True)
        if not acquired:
            return False
        try:
            for attempt in range(len(backoff_delays) + 1):
                try:
                    rate_limiter.wait_for_turn()
                    phonetic = phonetic_lookup(w) if phonetic_lookup is not None else None
                    audio = synthesize_word_to_bytes(
                        w,
                        _strip_word_tts_strategy_tag(model),
                        voice,
                        provider=provider,
                        content_mode=content_mode,
                        phonetic=phonetic,
                    )
                    write_bytes_atomically(out_path, audio)
                    return True
                except Exception as exc:
                    if _is_rate_limit_error(exc) and attempt < len(backoff_delays):
                        delay = backoff_delays[attempt]
                        rate_limiter.cooldown(delay)
                        print(f'[Word TTS 429] {w!r} backoff {delay}s (attempt {attempt+1})')
                        sleep(delay)
                        continue
                    with errors_lock:
                        errors.append(f'{w!r}: {exc}')
                    print(f'[Word TTS Error] {w!r}: {exc}')
                    return False
        finally:
            sem.release()
            # No rate_interval sleep here — per-key semaphore already enforces
            # per-key concurrency (≤3 concurrent requests per key),
            # which keeps us safely within MiniMax RPM limits.

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = {executor.submit(process_word, w): w for w in words}

        for future in as_completed(futures):
            w = futures[future]
            try:
                was_new = future.result()
                with completed_lock:
                    done_count += 1
                    if was_new:
                        generated += 1
                        completed += 1
                if done_count % progress_every == 0 or completed == total:
                    emit_progress('running', w)
            except Exception as exc:
                with errors_lock:
                    errors.append(f'{w!r}: {exc}')
                print(f'[Word TTS Future Error] {w!r}: {exc}')

    emit_progress('done', None)
    return {
        'total': total,
        'completed_initial': completed_initial,
        'completed_final': completed,
        'generated_this_run': generated,
        'errors': errors,
    }


def run_batch_generate_missing(
    book_ids: list[str] | None = None,
    *,
    cache_dir: Path | None = None,
    concurrency: int = 6,
    backoff_delays: tuple[float, ...] | None = None,
    rate_interval: float = 0.0,
    sleep_fn: Callable[[float], None] | None = None,
) -> dict:
    """
    Generate MP3 for every word in VOCAB_BOOKS (or subset) that is not yet cached.
    Uses DEFAULT_MODEL / DEFAULT_VOICE. Safe to re-run (skips existing files).
    """
    if cache_dir is None:
        cache_dir = word_tts_data_dir()
    else:
        cache_dir.mkdir(parents=True, exist_ok=True)

    words = collect_unique_words(book_ids)

    def write_default_progress(payload: dict) -> None:
        write_batch_progress(
            cache_dir,
            payload['total'],
            payload['completed_final'],
            payload['status'],
            current_word=payload.get('current_word'),
        )

    return run_batch_generate_words(
        words,
        cache_dir=cache_dir,
        concurrency=concurrency,
        backoff_delays=backoff_delays,
        rate_interval=rate_interval,
        sleep_fn=sleep_fn,
        progress_callback=write_default_progress,
    )
