from __future__ import annotations

import json
from pathlib import Path

from platform_sdk import follow_read_azure_assessment as azure


def _phoneme(value: str, score: int, *, candidates: list[dict] | None = None) -> dict:
    assessment = {'AccuracyScore': score}
    if candidates:
        assessment['NBestPhonemes'] = candidates
    return {
        'Phoneme': value,
        'PronunciationAssessment': assessment,
        'Offset': 100000,
        'Duration': 50000,
    }


def _payload(phonemes: list[dict], *, prosody: int | None = None) -> dict:
    assessment = {
        'AccuracyScore': 70,
        'CompletenessScore': 90,
        'FluencyScore': 84,
    }
    if prosody is not None:
        assessment['ProsodyScore'] = prosody
    return {
        'RecognitionStatus': 'Success',
        'NBest': [{
            'Display': 'language',
            'PronunciationAssessment': assessment,
            'Words': [{'Word': 'language', 'Phonemes': phonemes}],
        }],
    }


def test_azure_follow_read_builds_segment_and_phoneme_scores():
    gb = _payload([
        _phoneme('l', 90),
        _phoneme('æ', 80),
        _phoneme('ŋ', 70),
        _phoneme('g', 60),
        _phoneme('w', 50),
        _phoneme('ɪ', 40),
        _phoneme('dʒ', 30),
    ])
    us = _payload([
        _phoneme('l', 91),
        _phoneme('æ', 81, candidates=[{'Phoneme': 'e', 'Score': 62}]),
        _phoneme('ŋ', 71),
        _phoneme('g', 61),
        _phoneme('w', 51),
        _phoneme('ɪ', 41),
        _phoneme('dʒ', 31),
    ], prosody=73)

    result = azure._build_assessment(
        word='language',
        segments=[
            {'text': 'lan', 'phonetic': 'læŋ'},
            {'text': 'guage', 'phonetic': 'gwɪdʒ'},
        ],
        gb_payload=gb,
        us_payload=us,
    )

    assert result['provider'] == azure.AZURE_FOLLOW_READ_PROVIDER
    assert result['assessment_version'] == 'azure-pilot-v1'
    assert result['score'] == 67
    assert result['dimensions'] == {
        'phonemeAccuracy': 60,
        'completeness': 90,
        'fluency': 84,
        'prosody': 73,
    }
    assert result['segment_feedback'] == [
        {'text': 'lan', 'phonetic': 'læŋ', 'score': 80, 'status': 'ok', 'comment': 'lan /læŋ/ 建议重点重读。'},
        {'text': 'guage', 'phonetic': 'gwɪdʒ', 'score': 45, 'status': 'weak', 'comment': 'guage /gwɪdʒ/ 建议重点重读。'},
    ]
    assert result['phoneme_feedback'][1]['candidatePhonemes'] == [{'phoneme': 'e', 'confidence': 62}]
    assert result['weak_segments'] == ['guage']


def test_azure_follow_read_fails_closed_when_alignment_is_incomplete():
    try:
        azure._build_assessment(
            word='language',
            segments=[{'text': 'lan', 'phonetic': 'læŋ'}],
            gb_payload=_payload([_phoneme('l', 90), _phoneme('æ', 80)]),
            us_payload=_payload([_phoneme('l', 90), _phoneme('æ', 80)]),
        )
    except azure.AzureFollowReadAssessmentError as exc:
        assert '对齐失败' in str(exc)
    else:
        raise AssertionError('expected incomplete alignment to fail')


def test_azure_follow_read_pilot_word_flag_uses_manifest(monkeypatch, tmp_path):
    pilot_path = tmp_path / 'pilot.json'
    pilot_path.write_text(json.dumps({'words': ['language']}), encoding='utf-8')
    monkeypatch.setenv('FOLLOW_READ_AZURE_PILOT_WORDS_PATH', str(pilot_path))
    monkeypatch.setenv('FOLLOW_READ_AZURE_PILOT_ENABLED', 'true')
    azure.reset_azure_follow_read_pilot_cache()

    assert azure.is_azure_follow_read_pilot_word('Language') is True
    assert azure.is_azure_follow_read_pilot_word('phenomenon') is False


def test_azure_follow_read_pilot_defaults_on_when_credentials_exist(monkeypatch, tmp_path):
    pilot_path = tmp_path / 'pilot.json'
    pilot_path.write_text(json.dumps({'words': ['nearly']}), encoding='utf-8')
    monkeypatch.setenv('FOLLOW_READ_AZURE_PILOT_WORDS_PATH', str(pilot_path))
    monkeypatch.delenv('FOLLOW_READ_AZURE_PILOT_ENABLED', raising=False)
    monkeypatch.setenv('AZURE_SPEECH_KEY', 'test-key')
    monkeypatch.setenv('AZURE_SPEECH_REGION', 'eastus')
    azure.reset_azure_follow_read_pilot_cache()

    assert azure.is_azure_follow_read_pilot_word('nearly') is True


def test_follow_read_assessment_pilot_manifest_has_100_words():
    payload = json.loads(Path('vocabulary_data/follow_read_assessment_pilot.json').read_text(encoding='utf-8'))

    assert payload['assessment_version'] == 'azure-pilot-v1'
    assert len(payload['words']) == 100
    assert len(set(payload['words'])) == 100
    assert 'nearly' in payload['words']
    assert all(word.isalpha() for word in payload['words'])
