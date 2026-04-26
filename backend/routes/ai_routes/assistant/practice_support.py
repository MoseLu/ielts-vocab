from __future__ import annotations

from functools import lru_cache


@lru_cache(maxsize=1)
def _load_ai_practice_route_support():
    from services.ai_practice_support_service import (
        collocation_practice_response,
        correction_feedback_response,
        correct_text_response,
        game_attempt_response,
        game_session_start_response,
        game_state_response,
        game_themes_response,
        greet_response,
        ielts_example_response,
        pronunciation_check_response,
        review_plan_response,
        speaking_simulate_response,
        synonyms_diff_response,
        vocab_assessment_response,
        word_family_quiz_response,
        word_family_response,
    )

    return {
        'collocation_practice_response': collocation_practice_response,
        'correction_feedback_response': correction_feedback_response,
        'correct_text_response': correct_text_response,
        'game_attempt_response': game_attempt_response,
        'game_session_start_response': game_session_start_response,
        'game_state_response': game_state_response,
        'game_themes_response': game_themes_response,
        'greet_response': greet_response,
        'ielts_example_response': ielts_example_response,
        'pronunciation_check_response': pronunciation_check_response,
        'review_plan_response': review_plan_response,
        'speaking_simulate_response': speaking_simulate_response,
        'synonyms_diff_response': synonyms_diff_response,
        'vocab_assessment_response': vocab_assessment_response,
        'word_family_quiz_response': word_family_quiz_response,
        'word_family_response': word_family_response,
    }


@lru_cache(maxsize=1)
def _load_ai_speaking_route_support():
    from platform_sdk.ai_speaking_assessment_application import (
        build_speaking_prompt_response,
        evaluate_speaking_response,
        get_speaking_assessment_response,
        list_speaking_history_response,
    )

    return (
        build_speaking_prompt_response,
        evaluate_speaking_response,
        get_speaking_assessment_response,
        list_speaking_history_response,
    )


@ai_bp.route('/greet', methods=['POST'])
@token_required
def greet(current_user):
    return _load_ai_practice_route_support()['greet_response'](
        current_user,
        request.get_json(silent=True) or {},
    )


@ai_bp.route('/correct-text', methods=['POST'])
@token_required
def correct_text_api(current_user):
    return _load_ai_practice_route_support()['correct_text_response'](
        current_user,
        request.get_json() or {},
    )


@ai_bp.route('/correction-feedback', methods=['POST'])
@token_required
def correction_feedback(current_user):
    return _load_ai_practice_route_support()['correction_feedback_response'](
        current_user,
        request.get_json() or {},
    )


@ai_bp.route('/ielts-example', methods=['GET'])
@token_required
def ielts_example(current_user):
    return _load_ai_practice_route_support()['ielts_example_response'](current_user, request.args)


@ai_bp.route('/synonyms-diff', methods=['POST'])
@token_required
def synonyms_diff(current_user):
    return _load_ai_practice_route_support()['synonyms_diff_response'](
        current_user,
        request.get_json() or {},
    )


@ai_bp.route('/word-family', methods=['GET'])
@token_required
def word_family(current_user):
    return _load_ai_practice_route_support()['word_family_response'](current_user, request.args)


@ai_bp.route('/word-family/quiz', methods=['GET'])
@token_required
def word_family_quiz(current_user):
    return _load_ai_practice_route_support()['word_family_quiz_response'](current_user, request.args)


@ai_bp.route('/collocations/practice', methods=['GET'])
@token_required
def collocation_practice(current_user):
    return _load_ai_practice_route_support()['collocation_practice_response'](current_user, request.args)


@ai_bp.route('/practice/game/state', methods=['GET'])
@token_required
def practice_game_state(current_user):
    return _load_ai_practice_route_support()['game_state_response'](current_user, request.args)


@ai_bp.route('/practice/game/themes', methods=['GET'])
@token_required
def practice_game_themes(current_user):
    return _load_ai_practice_route_support()['game_themes_response'](current_user, request.args)


@ai_bp.route('/practice/game/session/start', methods=['POST'])
@token_required
def practice_game_session_start(current_user):
    return _load_ai_practice_route_support()['game_session_start_response'](
        current_user,
        request.get_json(silent=True) or {},
    )


@ai_bp.route('/practice/game/attempt', methods=['POST'])
@token_required
def practice_game_attempt(current_user):
    return _load_ai_practice_route_support()['game_attempt_response'](
        current_user,
        request.get_json(silent=True) or {},
    )


@ai_bp.route('/pronunciation-check', methods=['POST'])
@token_required
def pronunciation_check(current_user):
    return _load_ai_practice_route_support()['pronunciation_check_response'](
        current_user,
        request.get_json() or {},
    )


@ai_bp.route('/speaking-simulate', methods=['POST'])
@token_required
def speaking_simulate(current_user):
    return _load_ai_practice_route_support()['speaking_simulate_response'](
        current_user,
        request.get_json() or {},
    )


@ai_bp.route('/speaking/prompts', methods=['POST'])
@token_required
def speaking_prompts(current_user):
    build_speaking_prompt_response, _, _, _ = _load_ai_speaking_route_support()
    return build_speaking_prompt_response(current_user, request.get_json(silent=True) or {})


@ai_bp.route('/speaking/evaluate', methods=['POST'])
@token_required
def speaking_evaluate(current_user):
    _, evaluate_speaking_response, _, _ = _load_ai_speaking_route_support()
    return evaluate_speaking_response(current_user, request.form, request.files)


@ai_bp.route('/speaking/history', methods=['GET'])
@token_required
def speaking_history(current_user):
    _, _, _, list_speaking_history_response = _load_ai_speaking_route_support()
    return list_speaking_history_response(current_user, request.args)


@ai_bp.route('/speaking/history/<int:assessment_id>', methods=['GET'])
@token_required
def speaking_history_detail(current_user, assessment_id: int):
    _, _, get_speaking_assessment_response, _ = _load_ai_speaking_route_support()
    return get_speaking_assessment_response(current_user, assessment_id)


@ai_bp.route('/review-plan', methods=['GET'])
@token_required
def review_plan(current_user):
    return _load_ai_practice_route_support()['review_plan_response'](current_user)


@ai_bp.route('/vocab-assessment', methods=['GET'])
@token_required
def vocab_assessment(current_user):
    return _load_ai_practice_route_support()['vocab_assessment_response'](current_user, request.args)
