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


