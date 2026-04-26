from services.ai_assistant_tool_service import chat_with_tools
from services.ai_practice_support_service_parts import greet_and_text as _greet_and_text
from services.ai_practice_support_service_parts import lexical_tools as _lexical_tools
from services.ai_practice_support_service_parts import speaking_and_plans as _speaking_and_plans
from services.ai_route_support_service import _get_context_data
from platform_sdk.learner_profile_builder_adapter import build_learner_profile
from services.llm import correct_text


def _sync_greet_dependencies():
    _greet_and_text.chat_with_tools = chat_with_tools
    _greet_and_text._get_context_data = _get_context_data
    _greet_and_text.correct_text = correct_text


def _sync_plan_dependencies():
    _speaking_and_plans.build_learner_profile = build_learner_profile


def build_greet_fallback(current_user, ctx_data=None):
    return _greet_and_text.build_greet_fallback(current_user, ctx_data)


def greet_response(current_user, body):
    _sync_greet_dependencies()
    return _greet_and_text.greet_response(current_user, body)


def correct_text_response(current_user, body):
    _sync_greet_dependencies()
    return _greet_and_text.correct_text_response(current_user, body)


def correction_feedback_response(current_user, body):
    return _greet_and_text.correction_feedback_response(current_user, body)


def ielts_example_response(current_user, args):
    return _lexical_tools.ielts_example_response(current_user, args)


def synonyms_diff_response(current_user, body):
    return _lexical_tools.synonyms_diff_response(current_user, body)


def word_family_response(current_user, args):
    return _lexical_tools.word_family_response(current_user, args)


def word_family_quiz_response(current_user, args):
    return _lexical_tools.word_family_quiz_response(current_user, args)


def collocation_practice_response(current_user, args):
    return _lexical_tools.collocation_practice_response(current_user, args)


def game_state_response(current_user, args):
    return _speaking_and_plans.game_state_response(current_user, args)


def game_themes_response(current_user, args):
    return _speaking_and_plans.game_themes_response(current_user, args)


def game_session_start_response(current_user, body):
    return _speaking_and_plans.game_session_start_response(current_user, body)


def game_attempt_response(current_user, body):
    return _speaking_and_plans.game_attempt_response(current_user, body)


def pronunciation_check_response(current_user, body):
    return _speaking_and_plans.pronunciation_check_response(current_user, body)


def speaking_simulate_response(current_user, body):
    return _speaking_and_plans.speaking_simulate_response(current_user, body)


def review_plan_response(current_user):
    _sync_plan_dependencies()
    return _speaking_and_plans.review_plan_response(current_user)


def vocab_assessment_response(current_user, args):
    return _speaking_and_plans.vocab_assessment_response(current_user, args)


__all__ = [
    '_get_context_data',
    'build_greet_fallback',
    'build_learner_profile',
    'chat_with_tools',
    'collocation_practice_response',
    'correction_feedback_response',
    'correct_text',
    'correct_text_response',
    'game_attempt_response',
    'game_session_start_response',
    'game_state_response',
    'game_themes_response',
    'greet_response',
    'ielts_example_response',
    'pronunciation_check_response',
    'review_plan_response',
    'speaking_simulate_response',
    'synonyms_diff_response',
    'vocab_assessment_response',
    'word_family_quiz_response',
    'word_family_response',
]
