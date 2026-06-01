from __future__ import annotations

import base64
import json
import os
import subprocess
import tempfile
import unicodedata
from functools import lru_cache
from pathlib import Path

import imageio_ffmpeg
import requests


AZURE_FOLLOW_READ_PROVIDER = 'azure-pronunciation-dual-locale'
AZURE_FOLLOW_READ_ASSESSMENT_VERSION = 'azure-pilot-v1'
_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_PILOT_PATH = _REPO_ROOT / 'vocabulary_data' / 'follow_read_assessment_pilot.json'
_PHONEME_SEPARATORS = set(" /[].ˈˌ'-")
_PHONEME_MODIFIERS = {'ː', 'ˑ', '̯', 'ʰ', 'ʲ', 'ʷ', '̩'}
_MULTI_CHAR_PHONEMES = tuple(sorted({
    'tʃ', 'dʒ',
    'eɪ', 'aɪ', 'ɔɪ', 'aʊ', 'əʊ', 'oʊ',
    'ɪə', 'eə', 'ʊə', 'ɚ', 'ɝ',
}, key=len, reverse=True))


class AzureFollowReadAssessmentError(RuntimeError):
    pass


def _clamp_score(value) -> int:
    try:
        return max(0, min(100, int(round(float(value)))))
    except (TypeError, ValueError) as exc:
        raise AzureFollowReadAssessmentError('Azure 逐音素评分缺失') from exc


def _status_from_score(score: int) -> str:
    if score >= 85:
        return 'good'
    if score >= 60:
        return 'ok'
    return 'weak'


def _truthy_env(name: str, default: str = '') -> bool:
    return (os.environ.get(name, default) or '').strip().lower() in {'1', 'true', 'yes', 'on'}


def _has_azure_speech_credentials() -> bool:
    return bool((os.environ.get('AZURE_SPEECH_KEY') or '').strip() and (os.environ.get('AZURE_SPEECH_REGION') or '').strip())


def _pilot_path() -> Path:
    configured = (os.environ.get('FOLLOW_READ_AZURE_PILOT_WORDS_PATH') or '').strip()
    return Path(configured).resolve() if configured else _DEFAULT_PILOT_PATH


@lru_cache(maxsize=4)
def _load_pilot_words(path: str) -> frozenset[str]:
    try:
        payload = json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        raise AzureFollowReadAssessmentError('Azure 跟读灰度清单不可用') from exc
    words = payload.get('words') if isinstance(payload, dict) else None
    if not isinstance(words, list):
        raise AzureFollowReadAssessmentError('Azure 跟读灰度清单格式错误')
    return frozenset(str(word).strip().lower() for word in words if str(word).strip())


def reset_azure_follow_read_pilot_cache() -> None:
    _load_pilot_words.cache_clear()


def is_azure_follow_read_pilot_word(word: str) -> bool:
    configured = os.environ.get('FOLLOW_READ_AZURE_PILOT_ENABLED')
    enabled = _truthy_env('FOLLOW_READ_AZURE_PILOT_ENABLED') if configured is not None else _has_azure_speech_credentials()
    if not enabled:
        return False
    return str(word or '').strip().lower() in _load_pilot_words(str(_pilot_path()))


def split_ipa_phonemes(value: str | None) -> list[str]:
    text = str(value or '').strip()
    tokens: list[str] = []
    index = 0
    while index < len(text):
        char = text[index]
        if char in _PHONEME_SEPARATORS or char.isspace():
            index += 1
            continue
        token = next((item for item in _MULTI_CHAR_PHONEMES if text.startswith(item, index)), char)
        index += len(token)
        while index < len(text):
            modifier = text[index]
            if modifier in _PHONEME_MODIFIERS or unicodedata.combining(modifier):
                token += modifier
                index += 1
                continue
            break
        tokens.append(token)
    return tokens


def _azure_speech_key() -> str:
    key = (os.environ.get('AZURE_SPEECH_KEY') or '').strip()
    if not key:
        raise AzureFollowReadAssessmentError('Azure Speech API 密钥未配置')
    return key


def _azure_stt_endpoint(locale: str) -> str:
    region = (os.environ.get('AZURE_SPEECH_REGION') or '').strip()
    if not region:
        raise AzureFollowReadAssessmentError('Azure Speech 区域未配置')
    return (
        f'https://{region}.stt.speech.microsoft.com/'
        f'speech/recognition/conversation/cognitiveservices/v1?language={locale}&format=detailed'
    )


def _write_pcm_wav(audio_path: str) -> str:
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
        wav_path = temp_file.name
    command = [
        imageio_ffmpeg.get_ffmpeg_exe(),
        '-hide_banner',
        '-loglevel', 'error',
        '-y',
        '-i', audio_path,
        '-ac', '1',
        '-ar', '16000',
        '-c:a', 'pcm_s16le',
        wav_path,
    ]
    try:
        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=12)
    except (OSError, subprocess.SubprocessError) as exc:
        Path(wav_path).unlink(missing_ok=True)
        raise AzureFollowReadAssessmentError('跟读录音格式转换失败') from exc
    return wav_path


def _assessment_header(word: str, *, locale: str) -> str:
    payload = {
        'ReferenceText': word,
        'GradingSystem': 'HundredMark',
        'Granularity': 'Phoneme',
        'Dimension': 'Comprehensive',
        'EnableMiscue': 'True',
        'PhonemeAlphabet': 'IPA',
    }
    if locale == 'en-US':
        payload['EnableProsodyAssessment'] = 'True'
        payload['NBestPhonemeCount'] = 5
    encoded = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    return base64.b64encode(encoded).decode('ascii')


def _request_assessment(wav_path: str, *, word: str, locale: str) -> dict:
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'audio/wav; codecs=audio/pcm; samplerate=16000',
        'Ocp-Apim-Subscription-Key': _azure_speech_key(),
        'Pronunciation-Assessment': _assessment_header(word, locale=locale),
    }
    try:
        response = requests.post(
            _azure_stt_endpoint(locale),
            headers=headers,
            data=Path(wav_path).read_bytes(),
            timeout=15,
        )
    except (OSError, requests.RequestException) as exc:
        raise AzureFollowReadAssessmentError('Azure 逐音素评分暂时不可用') from exc
    if response.status_code >= 400:
        raise AzureFollowReadAssessmentError('Azure 逐音素评分暂时不可用')
    try:
        payload = response.json()
    except ValueError as exc:
        raise AzureFollowReadAssessmentError('Azure 逐音素评分返回格式错误') from exc
    if payload.get('RecognitionStatus') != 'Success':
        raise AzureFollowReadAssessmentError('Azure 未识别到有效跟读')
    return payload


def _best_result(payload: dict) -> dict:
    candidates = payload.get('NBest')
    if not isinstance(candidates, list) or not candidates or not isinstance(candidates[0], dict):
        raise AzureFollowReadAssessmentError('Azure 逐音素评分缺少详细结果')
    return candidates[0]


def _flatten_phonemes(best: dict) -> list[dict]:
    words = best.get('Words')
    if not isinstance(words, list):
        return []
    return [
        phoneme
        for word in words
        if isinstance(word, dict)
        for phoneme in (word.get('Phonemes') or [])
        if isinstance(phoneme, dict)
    ]


def _all_words_omitted(best: dict) -> bool:
    words = best.get('Words')
    return bool(words) and all(
        isinstance(word, dict)
        and (word.get('PronunciationAssessment') or {}).get('ErrorType') == 'Omission'
        for word in words
    )


def _phoneme_score(item: dict) -> int:
    assessment = item.get('PronunciationAssessment') or {}
    return _clamp_score(assessment.get('AccuracyScore'))


def _candidate_phonemes(item: dict | None) -> list[dict]:
    assessment = (item or {}).get('PronunciationAssessment') or {}
    raw_candidates = assessment.get('NBestPhonemes') or []
    return [
        {'phoneme': str(candidate.get('Phoneme') or '').strip(), 'confidence': _clamp_score(candidate.get('Score'))}
        for candidate in raw_candidates[:3]
        if isinstance(candidate, dict) and str(candidate.get('Phoneme') or '').strip()
    ]


def _normalize_phoneme(value: str) -> str:
    return ''.join(char for char in str(value or '').strip().lower() if char not in _PHONEME_SEPARATORS)


def _align_us_phonemes(expected: list[str], raw_items: list[dict]) -> list[dict | None]:
    actual = [_normalize_phoneme(item.get('Phoneme')) for item in raw_items]
    rows, cols = len(expected) + 1, len(actual) + 1
    scores = [[0] * cols for _ in range(rows)]
    moves = [[''] * cols for _ in range(rows)]
    for index in range(1, rows):
        scores[index][0], moves[index][0] = -index, 'expected'
    for index in range(1, cols):
        scores[0][index], moves[0][index] = -index, 'actual'
    for row in range(1, rows):
        for col in range(1, cols):
            matched = _normalize_phoneme(expected[row - 1]) == actual[col - 1]
            options = [
                (scores[row - 1][col - 1] + (2 if matched else 0), 'match'),
                (scores[row - 1][col] - 1, 'expected'),
                (scores[row][col - 1] - 1, 'actual'),
            ]
            scores[row][col], moves[row][col] = max(options, key=lambda item: item[0])
    aligned: list[dict | None] = [None] * len(expected)
    row, col = len(expected), len(actual)
    while row or col:
        move = moves[row][col]
        if move == 'match':
            aligned[row - 1] = raw_items[col - 1]
            row -= 1
            col -= 1
        elif move == 'expected':
            row -= 1
        else:
            col -= 1
    return aligned


def _summary(score: int, weak_segments: list[str]) -> str:
    if weak_segments:
        return f"已完成逐音素评分，优先重读 {'、'.join(weak_segments[:3])}，再连回完整单词。"
    if score >= 85:
        return '发音整体清晰稳定，可以保持当前节奏继续练习。'
    return '发音基本完整，建议对照示范再慢读一遍，稳定音长和衔接。'


def _feedback(summary: str) -> dict:
    return {
        'summary': summary,
        'stress': '重音以 en-GB 主评分为准，先保证目标音素完整清晰。',
        'vowel': '元音问题请查看红色或黄色音素，再对照示范慢读。',
        'consonant': '辅音问题请查看逐音素详情里的弱项提示。',
        'ending': '词尾音素如果偏低，请读完最后一个音后再结束录音。',
        'rhythm': '韵律仅作参考，第一版不参与最终分数。',
    }


def _build_assessment(*, word: str, segments: list[dict], gb_payload: dict, us_payload: dict) -> dict:
    gb_best = _best_result(gb_payload)
    us_best = _best_result(us_payload)
    specs = [
        {
            'text': str(segment.get('text') or segment.get('letters') or '').strip(),
            'phonetic': str(segment.get('phonetic') or '').strip(),
        }
        for segment in segments
        if str(segment.get('text') or segment.get('letters') or '').strip()
    ]
    expected_by_segment = [split_ipa_phonemes(spec['phonetic']) for spec in specs]
    expected = [phoneme for items in expected_by_segment for phoneme in items]
    if not expected or any(not items for items in expected_by_segment):
        raise AzureFollowReadAssessmentError('逐音素评分缺少标准音标')
    gb_items = _flatten_phonemes(gb_best)
    if not gb_items and _all_words_omitted(gb_best):
        gb_items = [{'PronunciationAssessment': {'AccuracyScore': 0}} for _ in expected]
    if len(gb_items) != len(expected):
        raise AzureFollowReadAssessmentError('逐音素评分对齐失败，请重新跟读')
    us_aligned = _align_us_phonemes(expected, _flatten_phonemes(us_best))
    phoneme_feedback = []
    for expected_phoneme, gb_item, us_item in zip(expected, gb_items, us_aligned):
        score = _phoneme_score(gb_item)
        phoneme_feedback.append({
            'expectedPhoneme': expected_phoneme,
            'score': score,
            'status': _status_from_score(score),
            'candidatePhonemes': _candidate_phonemes(us_item),
            'offsetMs': round(float(gb_item.get('Offset') or 0) / 10000),
            'durationMs': round(float(gb_item.get('Duration') or 0) / 10000),
        })
    segment_feedback = []
    cursor = 0
    for spec, phonemes in zip(specs, expected_by_segment):
        segment_scores = [item['score'] for item in phoneme_feedback[cursor:cursor + len(phonemes)]]
        cursor += len(phonemes)
        score = round(sum(segment_scores) / len(segment_scores))
        status = _status_from_score(score)
        segment_feedback.append({
            'text': spec['text'],
            'phonetic': spec['phonetic'],
            'score': score,
            'status': status,
            'comment': f"{spec['text']} /{spec['phonetic']}/ {'读得稳定' if status == 'good' else '建议重点重读'}。",
        })
    gb_assessment = gb_best.get('PronunciationAssessment') or {}
    us_assessment = us_best.get('PronunciationAssessment') or {}
    dimensions = {
        'phonemeAccuracy': round(sum(item['score'] for item in phoneme_feedback) / len(phoneme_feedback)),
        'completeness': _clamp_score(gb_assessment.get('CompletenessScore')),
        'fluency': _clamp_score(gb_assessment.get('FluencyScore')),
    }
    if us_assessment.get('ProsodyScore') is not None:
        dimensions['prosody'] = _clamp_score(us_assessment.get('ProsodyScore'))
    score = round(
        dimensions['phonemeAccuracy'] * 0.75
        + dimensions['completeness'] * 0.15
        + dimensions['fluency'] * 0.10
    )
    weak_segments = [item['text'] for item in segment_feedback if item['status'] == 'weak']
    return {
        'score': score,
        'transcript': str(gb_best.get('Display') or gb_best.get('Lexical') or word).strip(),
        'feedback': _feedback(_summary(score, weak_segments)),
        'segment_feedback': segment_feedback,
        'phoneme_feedback': phoneme_feedback,
        'weak_segments': weak_segments,
        'dimensions': dimensions,
        'provider': AZURE_FOLLOW_READ_PROVIDER,
        'model': 'azure-rest:en-GB+en-US',
        'assessment_version': AZURE_FOLLOW_READ_ASSESSMENT_VERSION,
    }


def run_azure_follow_read_assessment(*, audio_path: str, word: str, segments: list[dict]) -> tuple[dict, str]:
    wav_path = _write_pcm_wav(audio_path)
    try:
        gb_payload = _request_assessment(wav_path, word=word, locale='en-GB')
        us_payload = _request_assessment(wav_path, word=word, locale='en-US')
        result = _build_assessment(word=word, segments=segments, gb_payload=gb_payload, us_payload=us_payload)
        return result, result['model']
    finally:
        Path(wav_path).unlink(missing_ok=True)
