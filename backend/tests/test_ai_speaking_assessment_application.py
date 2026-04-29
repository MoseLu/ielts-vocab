from __future__ import annotations

import json

from platform_sdk import ai_speaking_assessment_application
from platform_sdk import ai_follow_read_assessment_application


def test_score_to_band_uses_half_band_thresholds():
    assert ai_speaking_assessment_application._score_to_band(95) == 9.0
    assert ai_speaking_assessment_application._score_to_band(76) == 7.5
    assert ai_speaking_assessment_application._score_to_band(62) == 6.5
    assert ai_speaking_assessment_application._score_to_band(0) == 0.0


def test_score_to_band_uses_custom_thresholds_from_env(monkeypatch):
    monkeypatch.setenv(
        'SPEAKING_ASSESSMENT_BAND_THRESHOLDS_JSON',
        json.dumps([[80, 8.0], [60, 6.0], [0, 0.0]]),
    )

    assert ai_speaking_assessment_application._score_to_band(85) == 8.0
    assert ai_speaking_assessment_application._score_to_band(60) == 6.0
    assert ai_speaking_assessment_application._score_to_band(20) == 0.0


def test_score_to_band_falls_back_when_custom_thresholds_are_invalid(monkeypatch):
    monkeypatch.setenv('SPEAKING_ASSESSMENT_BAND_THRESHOLDS_JSON', '{"bad": true}')

    assert ai_speaking_assessment_application._score_to_band(62) == 6.5


def test_round_half_band_uses_half_up_rounding():
    assert ai_speaking_assessment_application._round_half_band(7.24) == 7.0
    assert ai_speaking_assessment_application._round_half_band(7.25) == 7.5
    assert ai_speaking_assessment_application._round_half_band(7.75) == 8.0


def test_validate_assessment_payload_requires_dimension_feedback():
    payload = {
        'raw_scores': {
            'fluency': 78,
            'lexical': 71,
            'grammar': 69,
            'pronunciation': 74,
        },
        'feedback': {
            'summary': 'Overall understandable.',
            'dimension_feedback': {
                'fluency': 'Mostly fluent.',
                'lexical': 'Adequate vocabulary.',
                'grammar': '',
                'pronunciation': 'Clear enough.',
            },
        },
    }

    try:
        ai_speaking_assessment_application._validate_assessment_payload(payload)
    except ai_speaking_assessment_application.SpeakingAssessmentError as exc:
        assert exc.status_code == 502
        assert '维度反馈文本' in str(exc)
    else:
        raise AssertionError('expected validation error')


def test_build_speaking_prompt_response_includes_target_words(app):
    with app.app_context():
        response, status = ai_speaking_assessment_application.build_speaking_prompt_response(
            None,
            {
                'part': 2,
                'topic': 'education',
                'targetWords': ['dynamic', 'coherent'],
            },
        )

    assert status == 200
    payload = response.get_json()
    assert 'dynamic, coherent' in payload['promptText']
    assert payload['recommendedDurationSeconds'] == 120
    assert len(payload['followUps']) == 2


def test_follow_read_score_bands():
    assert ai_follow_read_assessment_application.resolve_follow_read_score_band(59) == ('needs_work', False)
    assert ai_follow_read_assessment_application.resolve_follow_read_score_band(60) == ('near_pass', False)
    assert ai_follow_read_assessment_application.resolve_follow_read_score_band(79) == ('near_pass', False)
    assert ai_follow_read_assessment_application.resolve_follow_read_score_band(80) == ('pass', True)
