import os
import re

from services.word_tts_service.audio_cache_parts.identity_and_fetch import normalize_word_key


_AZURE_SPEECH_KEY = os.environ.get('AZURE_SPEECH_KEY', '').strip()
_AZURE_SPEECH_REGION = os.environ.get('AZURE_SPEECH_REGION', '').strip()
_AZURE_DEFAULT_VOICE = (
    os.environ.get('AZURE_TTS_VOICE', 'en-US-AndrewMultilingualNeural').strip()
    or 'en-US-AndrewMultilingualNeural'
)
_AZURE_DEFAULT_SENTENCE_VOICE = (
    os.environ.get('AZURE_TTS_SENTENCE_VOICE', '').strip()
    or os.environ.get('AZURE_TTS_VOICE', '').strip()
    or _AZURE_DEFAULT_VOICE
)
_AZURE_DEFAULT_WORD_VOICE = (
    os.environ.get('AZURE_TTS_WORD_VOICE', '').strip()
    or os.environ.get('WORD_TTS_VOICE', '').strip()
    or os.environ.get('AZURE_TTS_SENTENCE_VOICE', '').strip()
    or os.environ.get('AZURE_TTS_VOICE', '').strip()
    or 'en-GB-RyanNeural'
)
_AZURE_OUTPUT_FORMAT = (
    os.environ.get('AZURE_TTS_OUTPUT_FORMAT', 'audio-24khz-48kbitrate-mono-mp3').strip()
    or 'audio-24khz-48kbitrate-mono-mp3'
)
_AZURE_DEFAULT_MODEL = (
    os.environ.get('AZURE_TTS_MODEL', f'azure-rest:{_AZURE_OUTPUT_FORMAT}').strip()
    or f'azure-rest:{_AZURE_OUTPUT_FORMAT}'
)
_AZURE_RATE = os.environ.get('AZURE_TTS_RATE', '+0.00%').strip() or '+0.00%'
_AZURE_WORD_CACHE_TAG = 'azure-word-v5-ielts-rp-female-onset-buffer'
_AZURE_SENTENCE_CACHE_TAG = 'azure-sentence-v4-ielts-rp-female'
_AZURE_WORD_RATE = os.environ.get('AZURE_TTS_WORD_RATE', '-6.00%').strip() or '-6.00%'
_AZURE_SENTENCE_RATE = os.environ.get('AZURE_TTS_SENTENCE_RATE', '-2.00%').strip() or '-2.00%'
_AZURE_WORD_PITCH = os.environ.get('AZURE_TTS_WORD_PITCH', '').strip()
_AZURE_SENTENCE_PITCH = os.environ.get('AZURE_TTS_SENTENCE_PITCH', '').strip()
_AZURE_WORD_LEADING_BREAK_MS = os.environ.get('AZURE_TTS_WORD_LEADING_BREAK_MS', '100').strip() or '100'
_AZURE_WORD_TRAILING_BREAK_MS = os.environ.get('AZURE_TTS_WORD_TRAILING_BREAK_MS', '').strip()
_AZURE_WORD_AUDIO_DURATION_MS = os.environ.get('AZURE_TTS_WORD_AUDIO_DURATION_MS', '').strip()
_AZURE_WORD_SEGMENT_BREAK_MS = os.environ.get('AZURE_TTS_WORD_SEGMENT_BREAK_MS', '220').strip() or '220'
_AZURE_WORD_PRONUNCIATION_LOOKUP: dict[str, str] | None = None
_AZURE_WORDISH_TEXT_RE = re.compile(r"^[A-Za-z][A-Za-z' -]{0,79}$")
_AZURE_SEGMENTED_CONTENT_MODES = {'word-segmented', 'phonetic-segments'}
_AZURE_IPA_VOWELS = set('aeiouyɑɒæəɛɜɝɚɨɪʊʌɔœøɐʉʏɯɤ')
_AZURE_IPA_NUCLEUS_CONTINUATIONS = {'ː', 'ˑ', '̯'}
_AZURE_IPA_ONSETS = {
    'b', 'bl', 'br', 'd', 'dʒ', 'dj', 'dr', 'dw', 'f', 'fj', 'fl', 'fr',
    'g', 'gj', 'gl', 'gr', 'gw', 'h', 'hj', 'j', 'k', 'kj', 'kl', 'kr',
    'kw', 'l', 'lj', 'm', 'mj', 'n', 'nj', 'p', 'pj', 'pl', 'pr', 'r',
    's', 'sj', 'sk', 'skr', 'skw', 'sl', 'sm', 'sn', 'sp', 'spl', 'spr',
    'st', 'str', 'sw', 'ʃ', 'ʃr', 't', 'tʃ', 'tj', 'tr', 'tw', 'v', 'vr',
    'w', 'z', 'zj', 'zl', 'ð', 'θ', 'θr',
}


def _first_non_empty_env(*keys: str, default: str = '') -> str:
    for key in keys:
        value = os.environ.get(key, '').strip()
        if value:
            return value
    return (default or '').strip()


def azure_speech_key() -> str:
    key = os.environ.get('AZURE_SPEECH_KEY', _AZURE_SPEECH_KEY).strip()
    if not key:
        raise RuntimeError('AZURE_SPEECH_KEY environment variable is not set')
    return key


def azure_speech_region() -> str:
    region = os.environ.get('AZURE_SPEECH_REGION', _AZURE_SPEECH_REGION).strip()
    if not region:
        raise RuntimeError('AZURE_SPEECH_REGION environment variable is not set')
    return region


def azure_default_voice() -> str:
    return os.environ.get('AZURE_TTS_VOICE', _AZURE_DEFAULT_VOICE).strip() or _AZURE_DEFAULT_VOICE


def azure_sentence_voice() -> str:
    return _first_non_empty_env(
        'AZURE_TTS_SENTENCE_VOICE',
        'AZURE_TTS_VOICE',
        default=_AZURE_DEFAULT_SENTENCE_VOICE,
    )


def azure_word_voice() -> str:
    return _first_non_empty_env(
        'AZURE_TTS_WORD_VOICE',
        'WORD_TTS_VOICE',
        'AZURE_TTS_SENTENCE_VOICE',
        'AZURE_TTS_VOICE',
        default=_AZURE_DEFAULT_WORD_VOICE,
    )


def azure_output_format() -> str:
    return os.environ.get('AZURE_TTS_OUTPUT_FORMAT', _AZURE_OUTPUT_FORMAT).strip() or _AZURE_OUTPUT_FORMAT


def azure_default_model() -> str:
    fallback = f'azure-rest:{azure_output_format()}'
    return os.environ.get('AZURE_TTS_MODEL', _AZURE_DEFAULT_MODEL).strip() or fallback


def azure_speech_endpoint() -> str:
    return f'https://{azure_speech_region()}.tts.speech.microsoft.com/cognitiveservices/v1'


def azure_voice_locale(voice: str) -> str:
    parts = (voice or '').split('-')
    if len(parts) >= 2:
        return f'{parts[0]}-{parts[1]}'
    return 'en-US'


def azure_rate_percent(speed: float | None = None) -> str:
    if speed is None:
        return os.environ.get('AZURE_TTS_RATE', _AZURE_RATE).strip() or _AZURE_RATE
    clamped = max(0.5, min(2.0, float(speed)))
    return f'{(clamped - 1.0) * 100.0:+.2f}%'


def detect_azure_content_mode(text: str, content_mode: str | None = None) -> str:
    resolved_mode = (content_mode or '').strip().lower()
    if resolved_mode == 'sentence':
        return resolved_mode
    if resolved_mode == 'word' or resolved_mode in _AZURE_SEGMENTED_CONTENT_MODES:
        return 'word'

    normalized_text = (text or '').strip()
    if not normalized_text:
        return 'sentence'

    token_count = len(normalized_text.split())
    if (
        token_count <= 3
        and _AZURE_WORDISH_TEXT_RE.fullmatch(normalized_text)
        and not any(char in normalized_text for char in '.?!,:;')
    ):
        return 'word'
    return 'sentence'


def is_segmented_azure_content_mode(content_mode: str | None = None) -> bool:
    return (content_mode or '').strip().lower() in _AZURE_SEGMENTED_CONTENT_MODES


def azure_rate_for_mode(
    text: str,
    *,
    content_mode: str | None = None,
    speed: float | None = None,
) -> str:
    if speed is not None:
        return azure_rate_percent(speed)
    resolved_mode = detect_azure_content_mode(text, content_mode)
    if resolved_mode == 'word':
        return os.environ.get('AZURE_TTS_WORD_RATE', _AZURE_WORD_RATE).strip() or _AZURE_WORD_RATE
    return os.environ.get('AZURE_TTS_SENTENCE_RATE', _AZURE_SENTENCE_RATE).strip() or _AZURE_SENTENCE_RATE


def azure_pitch_for_mode(text: str, *, content_mode: str | None = None) -> str:
    resolved_mode = detect_azure_content_mode(text, content_mode)
    if resolved_mode == 'word':
        return os.environ.get('AZURE_TTS_WORD_PITCH', _AZURE_WORD_PITCH).strip() or _AZURE_WORD_PITCH
    return os.environ.get('AZURE_TTS_SENTENCE_PITCH', _AZURE_SENTENCE_PITCH).strip() or _AZURE_SENTENCE_PITCH


def azure_voice_for_mode(text: str, *, content_mode: str | None = None) -> str:
    resolved_mode = detect_azure_content_mode(text, content_mode)
    if resolved_mode == 'word':
        return azure_word_voice()
    return azure_sentence_voice()


def normalize_azure_ipa(phonetic: str | None) -> str:
    value = str(phonetic or '').strip()
    if not value:
        return ''
    if len(value) >= 2 and value[0] in '/[' and value[-1] in '/]':
        value = value[1:-1]
    value = value.replace('(', '').replace(')', '')
    value = value.replace('·', '.')
    value = value.replace("'", 'ˈ')
    value = value.replace('（', '').replace('）', '')
    value = re.sub(r'\s+', ' ', value)
    value = value.strip().strip('/').strip()
    return value


def azure_word_trailing_break_ms() -> str:
    raw = os.environ.get(
        'AZURE_TTS_WORD_TRAILING_BREAK_MS',
        _AZURE_WORD_TRAILING_BREAK_MS,
    ).strip()
    if not raw:
        return ''
    try:
        value = max(0, min(500, int(raw)))
    except ValueError:
        return ''
    return str(value)


def azure_word_leading_break_ms() -> str:
    raw = os.environ.get(
        'AZURE_TTS_WORD_LEADING_BREAK_MS',
        _AZURE_WORD_LEADING_BREAK_MS,
    ).strip()
    if not raw:
        return ''
    try:
        value = max(0, min(400, int(raw)))
    except ValueError:
        return ''
    return str(value)


def azure_word_audio_duration_ms() -> str:
    raw = os.environ.get(
        'AZURE_TTS_WORD_AUDIO_DURATION_MS',
        _AZURE_WORD_AUDIO_DURATION_MS,
    ).strip()
    if not raw:
        return ''
    try:
        value = max(0, min(2000, int(raw)))
    except ValueError:
        return ''
    return str(value)


def azure_word_segment_break_ms() -> str:
    raw = os.environ.get(
        'AZURE_TTS_WORD_SEGMENT_BREAK_MS',
        _AZURE_WORD_SEGMENT_BREAK_MS,
    ).strip()
    if not raw:
        return '220'
    try:
        value = max(80, min(800, int(raw)))
    except ValueError:
        return '220'
    return str(value)


def _build_azure_word_pronunciation_lookup() -> dict[str, str]:
    from services import books_catalog_service, books_registry_service

    lookup: dict[str, str] = {}
    for book in books_registry_service.list_vocab_books():
        vocabulary = books_catalog_service.load_book_vocabulary(book['id']) or []
        for entry in vocabulary:
            normalized_word = normalize_word_key(entry.get('word'))
            phonetic = normalize_azure_ipa(entry.get('phonetic'))
            if not normalized_word or not phonetic or normalized_word in lookup:
                continue
            lookup[normalized_word] = phonetic
    return lookup


def lookup_azure_word_phonetic(text: str) -> str:
    global _AZURE_WORD_PRONUNCIATION_LOOKUP

    normalized_word = normalize_word_key(text)
    if not normalized_word:
        return ''
    if _AZURE_WORD_PRONUNCIATION_LOOKUP is None:
        try:
            _AZURE_WORD_PRONUNCIATION_LOOKUP = _build_azure_word_pronunciation_lookup()
        except Exception:
            _AZURE_WORD_PRONUNCIATION_LOOKUP = {}
    return _AZURE_WORD_PRONUNCIATION_LOOKUP.get(normalized_word, '')


def _split_explicit_azure_ipa_syllables(phonetic: str) -> list[str]:
    segments = [segment.strip() for segment in phonetic.split('.') if segment.strip()]
    if len(segments) <= 1:
        return segments

    normalized_segments: list[str] = []
    for segment in segments:
        chunk = segment
        while True:
            split_index = -1
            for marker in ('ˈ', 'ˌ'):
                marker_index = chunk.find(marker, 1)
                if marker_index > 0 and (split_index < 0 or marker_index < split_index):
                    split_index = marker_index
            if split_index <= 0:
                break
            prefix = chunk[:split_index].strip()
            if prefix:
                normalized_segments.append(prefix)
            chunk = chunk[split_index:]
        if chunk.strip():
            normalized_segments.append(chunk.strip())
    return normalized_segments


def _best_azure_onset_length(cluster: str) -> int:
    cleaned = (cluster or '').strip()
    if not cleaned:
        return 0
    for length in range(len(cleaned), 0, -1):
        if cleaned[-length:] in _AZURE_IPA_ONSETS:
            return length
    return 1


def _boundary_after_nonstress_chars(middle: str, prefix_length: int) -> int:
    if prefix_length <= 0:
        return 0
    nonstress_seen = 0
    for index, char in enumerate(middle):
        if char not in {'ˈ', 'ˌ'}:
            nonstress_seen += 1
        if nonstress_seen >= prefix_length:
            return index + 1
    return len(middle)


def split_azure_ipa_syllables(phonetic: str | None) -> list[str]:
    normalized = normalize_azure_ipa(phonetic)
    if not normalized:
        return []

    explicit_segments = _split_explicit_azure_ipa_syllables(normalized)
    if len(explicit_segments) > 1:
        return explicit_segments

    nuclei: list[tuple[int, int]] = []
    index = 0
    while index < len(normalized):
        if normalized[index] in _AZURE_IPA_VOWELS:
            start = index
            index += 1
            while index < len(normalized) and (
                normalized[index] in _AZURE_IPA_VOWELS
                or normalized[index] in _AZURE_IPA_NUCLEUS_CONTINUATIONS
            ):
                index += 1
            nuclei.append((start, index))
            continue
        index += 1

    if len(nuclei) <= 1:
        return [normalized]

    syllables: list[str] = []
    syllable_start = 0
    for previous, following in zip(nuclei, nuclei[1:]):
        middle = normalized[previous[1]:following[0]]
        without_stress = middle.replace('ˈ', '').replace('ˌ', '')
        onset_length = _best_azure_onset_length(without_stress)
        prefix_length = max(0, len(without_stress) - onset_length)
        boundary = previous[1] + _boundary_after_nonstress_chars(middle, prefix_length)
        syllable = normalized[syllable_start:boundary].strip()
        if syllable:
            syllables.append(syllable)
        syllable_start = boundary

    tail = normalized[syllable_start:].strip()
    if tail:
        syllables.append(tail)
    return syllables or [normalized]


def build_azure_ssml(
    text: str,
    voice: str | None = None,
    *,
    rate: str | None = None,
    content_mode: str | None = None,
    phonetic: str | None = None,
    pitch: str | None = None,
    use_lookup_phonetic: bool = True,
) -> str:
    from xml.sax.saxutils import escape

    resolved_mode = detect_azure_content_mode(text, content_mode)
    resolved_voice = (voice or '').strip() or azure_voice_for_mode(text, content_mode=resolved_mode)
    resolved_rate = rate or azure_rate_for_mode(text, content_mode=resolved_mode)
    resolved_pitch = pitch if pitch is not None else azure_pitch_for_mode(text, content_mode=resolved_mode)
    locale = azure_voice_locale(resolved_voice)
    escaped_text = escape(text or '')
    resolved_phonetic = normalize_azure_ipa(phonetic)
    if not resolved_phonetic and resolved_mode == 'word' and use_lookup_phonetic:
        resolved_phonetic = lookup_azure_word_phonetic(text)

    if resolved_phonetic and is_segmented_azure_content_mode(content_mode):
        syllables = split_azure_ipa_syllables(resolved_phonetic)
        if len(syllables) > 1:
            segment_break = azure_word_segment_break_ms()
            fragments: list[str] = []
            for index, syllable in enumerate(syllables):
                escaped_syllable = escape(
                    syllable,
                    entities={'"': '&quot;', "'": '&apos;'},
                )
                fallback_text = escape(re.sub(r'[ˈˌ]', '', syllable) or (text or ''))
                fragments.append(
                    f"<phoneme alphabet='ipa' ph='{escaped_syllable}'>"
                    f'{fallback_text}'
                    '</phoneme>'
                )
                if index < len(syllables) - 1:
                    fragments.append(f"<break time='{segment_break}ms'/>")
            content = ''.join(fragments)
        else:
            escaped_phonetic = escape(
                resolved_phonetic,
                entities={'"': '&quot;', "'": '&apos;'},
            )
            content = (
                f"<phoneme alphabet='ipa' ph='{escaped_phonetic}'>"
                f'{escaped_text}'
                '</phoneme>'
            )
    elif resolved_phonetic:
        escaped_phonetic = escape(
            resolved_phonetic,
            entities={'"': '&quot;', "'": '&apos;'},
        )
        content = (
            f"<phoneme alphabet='ipa' ph='{escaped_phonetic}'>"
            f'{escaped_text}'
            '</phoneme>'
        )
    else:
        content = escaped_text

    prosody_attrs = [f"rate='{resolved_rate}'"]
    if resolved_pitch:
        prosody_attrs.append(f"pitch='{escape(resolved_pitch)}'")
    content = f"<prosody {' '.join(prosody_attrs)}>{content}</prosody>"

    leading_break_ms = azure_word_leading_break_ms()
    trailing_break_ms = azure_word_trailing_break_ms()
    word_audio_duration_ms = azure_word_audio_duration_ms()
    voice_prefix = ''
    speak_attrs = ["version='1.0'", f"xml:lang='{locale}'"]
    if resolved_mode == 'word' and word_audio_duration_ms:
        speak_attrs.append("xmlns:mstts='http://www.w3.org/2001/mstts'")
        voice_prefix = f"<mstts:audioduration value='{word_audio_duration_ms}ms'/>"
    if resolved_mode == 'word' and leading_break_ms:
        content = f"<break time='{leading_break_ms}ms'/>{content}"
    if resolved_mode == 'word' and trailing_break_ms:
        content = f"{content}<break time='{trailing_break_ms}ms'/>"
    content = f'{voice_prefix}{content}'
    return (
        "<speak {speak_attrs}>"
        "<voice name='{voice}'>"
        '{content}'
        "</voice>"
        "</speak>"
    ).format(
        speak_attrs=' '.join(speak_attrs),
        voice=resolved_voice,
        content=content,
    )
