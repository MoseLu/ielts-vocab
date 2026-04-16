from services.ai_practice_support_service import (
    build_greet_fallback as _build_greet_fallback,
    collocation_practice_response as _collocation_practice_response,
    correction_feedback_response as _correction_feedback_response,
    correct_text_response as _correct_text_response,
    game_attempt_response as _game_attempt_response,
    game_state_response as _game_state_response,
    greet_response as _greet_response,
    ielts_example_response as _ielts_example_response,
    pronunciation_check_response as _pronunciation_check_response,
    review_plan_response as _review_plan_response,
    speaking_simulate_response as _speaking_simulate_response,
    synonyms_diff_response as _synonyms_diff_response,
    vocab_assessment_response as _vocab_assessment_response,
    word_family_quiz_response as _word_family_quiz_response,
    word_family_response as _word_family_response,
)
from platform_sdk.ai_speaking_assessment_application import (
    build_speaking_prompt_response as _build_speaking_prompt_response,
    evaluate_speaking_response as _evaluate_speaking_response,
    get_speaking_assessment_response as _get_speaking_assessment_response,
    list_speaking_history_response as _list_speaking_history_response,
)


@ai_bp.route('/greet', methods=['POST'])
@token_required
def greet(current_user):
    return _greet_response(current_user, request.get_json(silent=True) or {})


@ai_bp.route('/correct-text', methods=['POST'])
@token_required
def correct_text_api(current_user):
    return _correct_text_response(current_user, request.get_json() or {})


@ai_bp.route('/correction-feedback', methods=['POST'])
@token_required
def correction_feedback(current_user):
    return _correction_feedback_response(current_user, request.get_json() or {})


@ai_bp.route('/ielts-example', methods=['GET'])
@token_required
def ielts_example(current_user):
    return _ielts_example_response(current_user, request.args)


@ai_bp.route('/synonyms-diff', methods=['POST'])
@token_required
def synonyms_diff(current_user):
    return _synonyms_diff_response(current_user, request.get_json() or {})


@ai_bp.route('/word-family', methods=['GET'])
@token_required
def word_family(current_user):
    return _word_family_response(current_user, request.args)


@ai_bp.route('/word-family/quiz', methods=['GET'])
@token_required
def word_family_quiz(current_user):
    return _word_family_quiz_response(current_user, request.args)


@ai_bp.route('/collocations/practice', methods=['GET'])
@token_required
def collocation_practice(current_user):
    return _collocation_practice_response(current_user, request.args)


@ai_bp.route('/practice/game/state', methods=['GET'])
@token_required
def practice_game_state(current_user):
    return _game_state_response(current_user, request.args)


@ai_bp.route('/practice/game/attempt', methods=['POST'])
@token_required
def practice_game_attempt(current_user):
    return _game_attempt_response(current_user, request.get_json(silent=True) or {})


@ai_bp.route('/pronunciation-check', methods=['POST'])
@token_required
def pronunciation_check(current_user):
    return _pronunciation_check_response(current_user, request.get_json() or {})


@ai_bp.route('/speaking-simulate', methods=['POST'])
@token_required
def speaking_simulate(current_user):
    return _speaking_simulate_response(current_user, request.get_json() or {})


@ai_bp.route('/speaking/prompts', methods=['POST'])
@token_required
def speaking_prompts(current_user):
    return _build_speaking_prompt_response(current_user, request.get_json(silent=True) or {})


@ai_bp.route('/speaking/evaluate', methods=['POST'])
@token_required
def speaking_evaluate(current_user):
    return _evaluate_speaking_response(current_user, request.form, request.files)


@ai_bp.route('/speaking/history', methods=['GET'])
@token_required
def speaking_history(current_user):
    return _list_speaking_history_response(current_user, request.args)


@ai_bp.route('/speaking/history/<int:assessment_id>', methods=['GET'])
@token_required
def speaking_history_detail(current_user, assessment_id: int):
    return _get_speaking_assessment_response(current_user, assessment_id)


@ai_bp.route('/review-plan', methods=['GET'])
@token_required
def review_plan(current_user):
    return _review_plan_response(current_user)


@ai_bp.route('/vocab-assessment', methods=['GET'])
@token_required
def vocab_assessment(current_user):
    return _vocab_assessment_response(current_user, request.args)
