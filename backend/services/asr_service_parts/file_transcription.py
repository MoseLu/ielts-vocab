def _configure_dashscope_file_client() -> None:
    dashscope.api_key = get_dashscope_api_key()
    dashscope.base_websocket_api_url = DASHSCOPE_FILE_WS_URL


def _detect_uploaded_audio_suffix(audio_file) -> tuple[str, str]:
    suffix = '.webm'
    content_type = (getattr(audio_file, 'content_type', '') or '').lower()

    if 'wav' in content_type:
        suffix = '.wav'
    elif 'ogg' in content_type:
        suffix = '.ogg'
    elif 'mp4' in content_type or 'mpeg' in content_type:
        suffix = '.mp4'

    return suffix, content_type


def _convert_uploaded_audio_to_pcm(source_path: str, source_suffix: str) -> str:
    pcm_path = source_path.replace(source_suffix, '.pcm')
    result = subprocess.run(
        [
            FFMPEG_EXE,
            '-i',
            source_path,
            '-ar',
            '16000',
            '-ac',
            '1',
            '-f',
            's16le',
            pcm_path,
            '-y',
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        print(f"FFmpeg error: {result.stderr}")
        raise ASRServiceError(f'音频转换失败: {result.stderr}')
    return pcm_path


def _create_file_recognition_callback(
    result_text: list[str],
    recognition_error: list[str],
    recognition_complete,
):
    class FileRecognitionCallback(RecognitionCallback):
        def on_event(self, result: RecognitionResult):
            sentence = result.get_sentence()
            if RecognitionResult.is_sentence_end(sentence):
                text = sentence.get('text', '').strip()
                if text:
                    result_text.append(text)
                    print(f"Final result: {text}")

        def on_complete(self):
            print("Recognition complete")
            recognition_complete.set()

        def on_error(self, message):
            print(f"Recognition error: {message}")
            recognition_error.append(str(message))
            recognition_complete.set()

    return FileRecognitionCallback()


def _recognize_pcm_audio(pcm_path: str, model: str) -> str:
    _configure_dashscope_file_client()

    result_text: list[str] = []
    recognition_error: list[str] = []
    recognition_complete = threading.Event()
    callback = _create_file_recognition_callback(
        result_text,
        recognition_error,
        recognition_complete,
    )
    recognition = Recognition(
        model=model,
        callback=callback,
        format='pcm',
        sample_rate=16000,
        language_hints=['en', 'zh'],
    )

    with open(pcm_path, 'rb') as pcm_file:
        audio_data = pcm_file.read()

    print(f"PCM file size: {len(audio_data)} bytes")

    recognition.start()
    chunk_size = 3200
    offset = 0
    while offset < len(audio_data):
        chunk = audio_data[offset:offset + chunk_size]
        recognition.send_audio_frame(chunk)
        offset += chunk_size
    recognition.stop()

    if not recognition_complete.wait(timeout=20):
        raise ASRServiceError('语音识别超时，请重试')
    if recognition_error and not result_text:
        raise ASRServiceError(recognition_error[0])

    return ' '.join(result_text).strip()


def transcribe_uploaded_audio(audio_file) -> str:
    if audio_file is None:
        raise ASRServiceError('未收到音频文件', status_code=400)

    suffix, content_type = _detect_uploaded_audio_suffix(audio_file)
    model = resolve_file_asr_model()

    print("\n=== Speech Recognition Request ===")
    print(f"Model: {model}")
    print(f"File suffix: {suffix}, Content-Type: {content_type}")

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        audio_file.save(tmp.name)
        tmp_path = tmp.name

    pcm_path = None
    try:
        pcm_path = _convert_uploaded_audio_to_pcm(tmp_path, suffix)
        print("Converted to PCM (16kHz mono)")
        return _recognize_pcm_audio(pcm_path, model)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        if pcm_path:
            try:
                os.unlink(pcm_path)
            except OSError:
                pass
