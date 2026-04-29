from platform_sdk.ai_practice_application import (
    collocation_practice_api_response,
    correction_feedback_api_response,
    correct_text_api_response,
    game_attempt_api_response,
    game_session_start_api_response,
    game_state_api_response,
    game_themes_api_response,
    greet_api_response,
    ielts_example_api_response,
    pronunciation_check_api_response,
    review_plan_api_response,
    speaking_simulate_api_response,
    synonyms_diff_api_response,
    vocab_assessment_api_response,
    word_family_api_response,
    word_family_quiz_api_response,
)
from platform_sdk.ai_speaking_assessment_application import (
    build_speaking_prompt_response,
    evaluate_speaking_response,
    get_speaking_assessment_response,
    list_speaking_history_response,
)
from platform_sdk.ai_follow_read_assessment_application import evaluate_follow_read_response


@ai_bp.route('/greet', methods=['POST'])
@token_required
def greet(current_user):
    return greet_api_response(current_user, request.get_json(silent=True) or {})


@ai_bp.route('/correct-text', methods=['POST'])
@token_required
def correct_text_api(current_user):
    return correct_text_api_response(current_user, request.get_json() or {})


@ai_bp.route('/correction-feedback', methods=['POST'])
@token_required
def correction_feedback(current_user):
    return correction_feedback_api_response(current_user, request.get_json() or {})


@ai_bp.route('/ielts-example', methods=['GET'])
@token_required
def ielts_example(current_user):
    return ielts_example_api_response(current_user, request.args)


@ai_bp.route('/synonyms-diff', methods=['POST'])
@token_required
def synonyms_diff(current_user):
    return synonyms_diff_api_response(current_user, request.get_json() or {})


@ai_bp.route('/word-family', methods=['GET'])
@token_required
def word_family(current_user):
    return word_family_api_response(current_user, request.args)


@ai_bp.route('/word-family/quiz', methods=['GET'])
@token_required
def word_family_quiz(current_user):
    return word_family_quiz_api_response(current_user, request.args)


@ai_bp.route('/collocations/practice', methods=['GET'])
@token_required
def collocation_practice(current_user):
    return collocation_practice_api_response(current_user, request.args)


@ai_bp.route('/practice/game/state', methods=['GET'])
@token_required
def practice_game_state(current_user):
    return game_state_api_response(current_user, request.args)


@ai_bp.route('/practice/game/themes', methods=['GET'])
@token_required
def practice_game_themes(current_user):
    return game_themes_api_response(current_user, request.args)


@ai_bp.route('/practice/game/session/start', methods=['POST'])
@token_required
def practice_game_session_start(current_user):
    return game_session_start_api_response(current_user, request.get_json(silent=True) or {})


@ai_bp.route('/practice/game/attempt', methods=['POST'])
@token_required
def practice_game_attempt(current_user):
    return game_attempt_api_response(current_user, request.get_json(silent=True) or {})


@ai_bp.route('/pronunciation-check', methods=['POST'])
@token_required
def pronunciation_check(current_user):
    return pronunciation_check_api_response(current_user, request.get_json() or {})


@ai_bp.route('/speaking-simulate', methods=['POST'])
@token_required
def speaking_simulate(current_user):
    return speaking_simulate_api_response(current_user, request.get_json() or {})


@ai_bp.route('/speaking/prompts', methods=['POST'])
@token_required
def speaking_prompts(current_user):
    return build_speaking_prompt_response(current_user, request.get_json(silent=True) or {})


@ai_bp.route('/speaking/evaluate', methods=['POST'])
@token_required
def speaking_evaluate(current_user):
    return evaluate_speaking_response(current_user, request.form, request.files)


@ai_bp.route('/follow-read/evaluate', methods=['POST'])
@token_required
def follow_read_evaluate(current_user):
    return evaluate_follow_read_response(current_user, request.form, request.files)


@ai_bp.route('/speaking/history', methods=['GET'])
@token_required
def speaking_history(current_user):
    return list_speaking_history_response(current_user, request.args)


@ai_bp.route('/speaking/history/<int:assessment_id>', methods=['GET'])
@token_required
def speaking_history_detail(current_user, assessment_id: int):
    return get_speaking_assessment_response(current_user, assessment_id)


@ai_bp.route('/review-plan', methods=['GET'])
@token_required
def review_plan(current_user):
    return review_plan_api_response(current_user)


@ai_bp.route('/vocab-assessment', methods=['GET'])
@token_required
def vocab_assessment(current_user):
    return vocab_assessment_api_response(current_user, request.args)
