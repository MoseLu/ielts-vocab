from routes import ai as ai_routes


def test_build_context_msg_includes_learner_profile_fields():
    rendered = ai_routes._build_context_msg({
        'practiceMode': 'meaning',
        'mode': 'review',
        'currentWord': 'affect',
        'currentFocusDimension': 'meaning',
        'weakestDimension': 'listening',
        'weakDimensionOrder': ['meaning', 'listening', 'dictation'],
        'weakFocusWords': ['effect', 'economic'],
        'recentWrongWords': ['effect', 'effort'],
        'trapStrategy': '错词回钩 + 易混词辨析',
    })

    assert 'effect' in rendered
    assert 'effort' in rendered
    assert 'trapStrategy' not in rendered
    assert '错词回钩' in rendered
