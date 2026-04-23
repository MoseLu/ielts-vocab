from __future__ import annotations

from functools import lru_cache


@lru_cache(maxsize=1)
def _load_context_route_support():
    from services.ai_assistant_memory_service import load_memory
    from services.ai_context_service import build_context_data
    from services.ai_learning_summary_service import alltime_words_display
    from services.books_catalog_service import serialize_effective_book_progress
    from services.books_registry_service import list_vocab_books

    return (
        alltime_words_display,
        build_context_data,
        list_vocab_books,
        load_memory,
        serialize_effective_book_progress,
    )


@lru_cache(maxsize=1)
def _load_profile_route_support():
    from platform_sdk.ai_home_todo_application import build_home_todos_response as home_todos_response
    from platform_sdk.learner_profile_builder_adapter import build_learner_profile as learner_profile_builder

    return home_todos_response, learner_profile_builder


def _get_context_data(user_id: int) -> dict:
    (
        alltime_words_display,
        build_context_data,
        list_vocab_books,
        load_memory,
        serialize_effective_book_progress,
    ) = _load_context_route_support()
    return build_context_data(
        user_id,
        alltime_words_display_resolver=alltime_words_display,
        load_memory_resolver=load_memory,
        load_vocab_books=list_vocab_books,
        serialize_effective_book_progress=serialize_effective_book_progress,
    )


def build_home_todos_response(*args, **kwargs):
    home_todos_response, _ = _load_profile_route_support()
    return home_todos_response(*args, **kwargs)


def build_learner_profile(*args, **kwargs):
    _, learner_profile_builder = _load_profile_route_support()
    return learner_profile_builder(*args, **kwargs)


@ai_bp.route('/context', methods=['GET'])
@token_required
def get_context(current_user: User):
    return jsonify(_get_context_data(current_user.id))


@ai_bp.route('/learner-profile', methods=['GET'])
@token_required
def get_learner_profile(current_user: User):
    target_date = request.args.get('date') or None
    view = request.args.get('view') or 'full'
    try:
        profile = build_learner_profile(current_user.id, target_date, view)
    except ValueError:
        return jsonify({'error': 'date must be YYYY-MM-DD'}), 400
    return jsonify(profile)


@ai_bp.route('/home-todos', methods=['GET'])
@token_required
def get_home_todos(current_user: User):
    payload, status = build_home_todos_response(
        current_user.id,
        target_date=request.args.get('date') or None,
    )
    return jsonify(payload), status
