def synthesize_word_to_bytes(
    text: str,
    model: str | None = None,
    voice: str | None = None,
    provider: str | None = None,
    speed: float | None = None,
    content_mode: str | None = None,
    phonetic: str | None = None,
) -> bytes:
    """
    Call MiniMax, DashScope, or Azure TTS and return MP3 bytes.
    Automatically dispatches based on _TTS_PROVIDER setting.
    Raises on any API failure.
    """
    import requests

    resolved_provider = (provider or _TTS_PROVIDER).strip().lower()

    if resolved_provider == 'hybrid':
        dictionary_audio = fetch_dictionary_word_audio_bytes(text)
        if dictionary_audio is not None:
            return dictionary_audio

        fallback_provider = _word_tts_fallback_provider()
        fallback_model = _strip_word_tts_strategy_tag(model)
        fallback_voice = (
            (voice or '').strip()
            or _provider_default_voice(fallback_provider)
        )
        return synthesize_word_to_bytes(
            text,
            fallback_model,
            fallback_voice,
            provider=fallback_provider,
            speed=speed,
            content_mode=content_mode,
            phonetic=phonetic,
        )

    if resolved_provider == 'azure':
        resolved_mode = detect_azure_content_mode(text, content_mode)
        requested_voice = (
            (voice or azure_voice_for_mode(text, content_mode=resolved_mode)).strip()
            or azure_voice_for_mode(text, content_mode=resolved_mode)
        )
        headers = {
            'Ocp-Apim-Subscription-Key': azure_speech_key(),
            'Ocp-Apim-Subscription-Region': azure_speech_region(),
            'Content-Type': 'application/ssml+xml; charset=utf-8',
            'X-Microsoft-OutputFormat': azure_output_format(),
            'User-Agent': 'ielts-vocab-backend',
        }
        ssml = build_azure_ssml(
            text,
            requested_voice,
            rate=azure_rate_for_mode(text, content_mode=resolved_mode, speed=speed),
            content_mode=content_mode or resolved_mode,
            phonetic=phonetic,
        )
        resp = requests.post(
            azure_speech_endpoint(),
            headers=headers,
            data=ssml,
            timeout=30,
        )
        if (
            resp.status_code == 400
            and resolved_mode == 'word'
            and "<phoneme alphabet='ipa'" in ssml
        ):
            resp = requests.post(
                azure_speech_endpoint(),
                headers=headers,
                data=build_azure_ssml(
                    text,
                    requested_voice,
                    rate=azure_rate_for_mode(text, content_mode=resolved_mode, speed=speed),
                    content_mode=content_mode or resolved_mode,
                    phonetic='',
                    use_lookup_phonetic=False,
                ),
                timeout=30,
            )
        if resp.status_code == 200:
            return ensure_mp3_bytes(resp.content)
        if resp.status_code == 429:
            raise DashScopeHTTPError('Azure TTS 429 rate limit exceeded', 429)
        raise DashScopeHTTPError(
            f'Azure TTS HTTP {resp.status_code}: {resp.text[:300]}',
            resp.status_code,
        )

    if resolved_provider in {'volcengine', 'doubao', 'bytedance', 'seedtts'}:
        import base64

        requested_voice = (voice or volcengine_default_voice()).strip() or volcengine_default_voice()
        payload = build_volcengine_tts_request(text, requested_voice, speed=speed)
        response = requests.post(
            volcengine_tts_endpoint(),
            headers={
                'Accept': 'text/event-stream',
                'Content-Type': 'application/json',
                'User-Agent': 'ielts-vocab-backend',
                'X-Api-App-Id': volcengine_tts_app_id(),
                'X-Api-Access-Key': volcengine_tts_access_key(),
                'X-Api-Request-Id': uuid.uuid4().hex,
                'X-Api-Resource-Id': volcengine_tts_resource_id(),
                'X-Control-Require-Usage-Tokens-Return': 'text_words',
            },
            json=payload,
            stream=True,
            timeout=(10, 60),
        )
        try:
            if response.status_code == 429:
                raise DashScopeHTTPError('Volcengine TTS 429 rate limit exceeded', 429)
            if response.status_code != 200:
                raise DashScopeHTTPError(
                    f'Volcengine TTS HTTP {response.status_code}: {response.text[:300]}',
                    response.status_code,
                )

            chunks: list[bytes] = []
            pending = ''
            for raw_line in response.iter_lines(decode_unicode=True):
                if raw_line is None:
                    continue
                line = raw_line.strip()
                if not line or line.startswith(':') or line.startswith('event:'):
                    continue
                if line.startswith('data:'):
                    line = line[5:].strip()
                pending = f'{pending}{line}' if pending else line
                try:
                    event = json.loads(pending)
                except json.JSONDecodeError:
                    continue
                pending = ''

                code = event.get('code')
                if code == 20000000:
                    break
                if code != 0:
                    message = (event.get('message') or 'unknown error').strip()
                    normalized = message.lower()
                    status_code = 429 if 'rate' in normalized or 'quota' in normalized else 502
                    raise DashScopeHTTPError(
                        f'Volcengine TTS error {code}: {message}',
                        status_code,
                    )

                data = event.get('data')
                if isinstance(data, dict):
                    data = data.get('audio') or data.get('data')
                if not data:
                    continue
                chunks.append(base64.b64decode(data))

            if not chunks:
                raise RuntimeError('Volcengine TTS response missing audio chunks')
            return ensure_mp3_bytes(b''.join(chunks))
        finally:
            response.close()

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
