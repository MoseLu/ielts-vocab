from __future__ import annotations

from platform_sdk.ai_practice_greet_application import (
    correction_feedback_response,
    correct_text_response,
    greet_response,
)
from platform_sdk.ai_practice_lexical_application import (
    collocation_practice_response,
    ielts_example_response,
    synonyms_diff_response,
    word_family_quiz_response,
    word_family_response,
)
from platform_sdk.ai_practice_game_application import (
    game_attempt_response,
    game_session_start_response,
    game_state_response,
    game_themes_response,
)
from platform_sdk.ai_practice_speaking_application import (
    pronunciation_check_response,
    review_plan_response,
    speaking_simulate_response,
    vocab_assessment_response,
)


def greet_api_response(current_user, body: dict | None):
    return greet_response(current_user, body or {})


def correct_text_api_response(current_user, body: dict | None):
    return correct_text_response(current_user, body or {})


def correction_feedback_api_response(current_user, body: dict | None):
    return correction_feedback_response(current_user, body or {})


def ielts_example_api_response(current_user, args):
    return ielts_example_response(current_user, args)


def synonyms_diff_api_response(current_user, body: dict | None):
    return synonyms_diff_response(current_user, body or {})


def word_family_api_response(current_user, args):
    return word_family_response(current_user, args)


def word_family_quiz_api_response(current_user, args):
    return word_family_quiz_response(current_user, args)


def collocation_practice_api_response(current_user, args):
    return collocation_practice_response(current_user, args)


def game_state_api_response(current_user, args):
    return game_state_response(current_user, args)


def game_themes_api_response(current_user, args):
    return game_themes_response(current_user, args)


def game_session_start_api_response(current_user, body: dict | None):
    return game_session_start_response(current_user, body or {})


def game_attempt_api_response(current_user, body: dict | None):
    return game_attempt_response(current_user, body or {})


def pronunciation_check_api_response(current_user, body: dict | None):
    return pronunciation_check_response(current_user, body or {})


def speaking_simulate_api_response(current_user, body: dict | None):
    return speaking_simulate_response(current_user, body or {})


def review_plan_api_response(current_user):
    return review_plan_response(current_user)


def vocab_assessment_api_response(current_user, args):
    return vocab_assessment_response(current_user, args)
