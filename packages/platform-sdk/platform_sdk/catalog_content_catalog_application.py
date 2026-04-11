from __future__ import annotations

from platform_sdk import catalog_content_confusable_support as confusable_support
from platform_sdk import notes_word_note_repository_adapter as word_note_repository
from platform_sdk.catalog_runtime_adapters import (
    books_vocabulary_loader_service,
    phonetic_lookup_service,
    word_catalog_repository,
)
from platform_sdk.catalog_provider_adapter import (
    build_book_response,
    build_book_chapters_response,
    build_books_response,
    build_search_words_response,
    ensure_word_catalog_entry,
    get_vocab_book,
    list_vocab_books,
    load_book_vocabulary,
    load_book_chapters,
    normalize_word_key,
)
from platform_sdk.learning_core_favorites_support import (
    FAVORITES_CHAPTER_ID,
    FAVORITES_CHAPTER_TITLE,
    _is_favorites_book,
    _serialize_favorite_words,
)
from platform_sdk.catalog_content_service_repositories import custom_book_catalog_service


WORD_NOTE_LIMIT = 500


def _find_book(book_id):
    return get_vocab_book(book_id)


def _paginate_items(items, page, per_page):
    start = (page - 1) * per_page
    end = start + per_page
    total = len(items)
    return {
        'items': items[start:end],
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': (total + per_page - 1) // per_page,
    }


def _chapter_id_matches(value, chapter_id):
    try:
        return int(value) == int(chapter_id)
    except (TypeError, ValueError):
        return str(value) == str(chapter_id)


def _strip_chapter_fields(word_entry):
    return {
        key: value
        for key, value in word_entry.items()
        if key not in {'chapter_id', 'chapter_title'}
    }


def build_categories_response():
    category_names = {
        'listening': '听力词汇',
        'reading': '阅读词汇',
        'writing': '写作词汇',
        'speaking': '口语词汇',
        'academic': '学术词汇',
        'comprehensive': '综合词汇',
        'confusable': '易混辨析',
        'phrases': '短语搭配',
    }
    categories = list(set(book['category'] for book in list_vocab_books()))
    return {
        'categories': [
            {'id': category, 'name': category_names.get(category, category)}
            for category in categories
        ]
    }, 200


def build_levels_response():
    level_names = {
        'beginner': '初级',
        'intermediate': '中级',
        'advanced': '高级',
    }
    levels = list(set(book['level'] for book in list_vocab_books()))
    return {
        'levels': [
            {'id': level, 'name': level_names.get(level, level)}
            for level in levels
        ]
    }, 200


def build_books_stats_response():
    books = list_vocab_books()
    total_words = sum(book['word_count'] for book in books)
    return {
        'total_books': len(books),
        'total_words': total_words,
        'categories': len(set(book['category'] for book in books)),
    }, 200


def _build_favorites_chapter_words_response(chapter_id):
    if not _chapter_id_matches(chapter_id, FAVORITES_CHAPTER_ID):
        return {'error': 'Chapter not found'}, 404

    current_user = confusable_support.resolve_optional_current_user()
    if not current_user:
        return {'error': 'Book not found'}, 404

    words = _serialize_favorite_words(current_user.id)
    if not words:
        return {'error': 'Chapter not found'}, 404

    return {
        'chapter': {
            'id': FAVORITES_CHAPTER_ID,
            'title': FAVORITES_CHAPTER_TITLE,
            'word_count': len(words),
            'is_custom': True,
        },
        'words': words,
    }, 200


def build_chapter_words_response(book_id, chapter_id):
    if _is_favorites_book(book_id):
        return _build_favorites_chapter_words_response(chapter_id)

    current_user = confusable_support.resolve_optional_current_user()
    custom_book = custom_book_catalog_service.get_custom_book_for_user(
        current_user.id if current_user else None,
        book_id,
    )
    if not custom_book and not _find_book(book_id):
        return {'error': 'Book not found'}, 404

    if confusable_support.is_confusable_match_book(book_id):
        custom_chapter = confusable_support.get_confusable_custom_chapter(
            current_user.id if current_user else None,
            chapter_id,
        )
        if custom_chapter:
            return {
                'chapter': {
                    'id': chapter_id,
                    'title': custom_chapter.title,
                    'word_count': int(custom_chapter.word_count or len(custom_chapter.words)),
                    'group_count': 1,
                    'is_custom': True,
                },
                'words': confusable_support.serialize_confusable_custom_words(custom_chapter),
            }, 200

    chapters_data = load_book_chapters(book_id)
    if not chapters_data:
        return {'error': 'Chapters not available for this book'}, 404

    chapter = next(
        (
            entry
            for entry in chapters_data.get('chapters', [])
            if _chapter_id_matches(entry.get('id'), chapter_id)
        ),
        None,
    )
    if not chapter:
        return {'error': 'Chapter not found'}, 404

    words = load_book_vocabulary(book_id)
    if words is None:
        return {'error': 'Failed to load chapter'}, 500

    chapter_words = [
        _strip_chapter_fields(word)
        for word in words
        if _chapter_id_matches(word.get('chapter_id'), chapter_id)
    ]
    return {'chapter': chapter, 'words': chapter_words}, 200


def build_book_words_response(book_id, page=1, per_page=100):
    if _is_favorites_book(book_id):
        current_user = confusable_support.resolve_optional_current_user()
        if not current_user:
            return {'error': 'Book not found'}, 404

        words = _serialize_favorite_words(current_user.id)
        if not words:
            return {'error': 'Book not found'}, 404
        paginated = _paginate_items(words, page, per_page)
        return {
            'words': paginated['items'],
            'total': paginated['total'],
            'page': paginated['page'],
            'per_page': paginated['per_page'],
            'total_pages': paginated['total_pages'],
        }, 200

    current_user = confusable_support.resolve_optional_current_user()
    if (
        not custom_book_catalog_service.get_custom_book_for_user(current_user.id if current_user else None, book_id)
        and not _find_book(book_id)
    ):
        return {'error': 'Book not found'}, 404

    words = load_book_vocabulary(book_id)
    if words is None:
        return {'error': 'Failed to load vocabulary'}, 500

    if confusable_support.is_confusable_match_book(book_id):
        custom_book = (
            confusable_support.get_confusable_custom_book(current_user.id)
            if current_user else None
        )
        if custom_book:
            custom_words = []
            for chapter in custom_book.chapters:
                try:
                    custom_chapter_id = int(str(chapter.id))
                except (TypeError, ValueError):
                    continue
                for word in confusable_support.serialize_confusable_custom_words(chapter):
                    custom_words.append({
                        **word,
                        'chapter_id': custom_chapter_id,
                        'chapter_title': chapter.title,
                    })
            if custom_words:
                words = [*words, *custom_words]

    paginated = _paginate_items(words, page, per_page)
    return {
        'words': paginated['items'],
        'total': paginated['total'],
        'page': paginated['page'],
        'per_page': paginated['per_page'],
        'total_pages': paginated['total_pages'],
    }, 200


def build_word_examples_response(
    *,
    single_word: str,
    batch_words: str,
) -> tuple[dict, int]:
    single = str(single_word or '').strip().lower()
    batch_raw = str(batch_words or '').strip()

    if single:
        result = {}
        hits = books_vocabulary_loader_service.resolve_unified_examples(single)
        if hits:
            result[single] = hits
        return {'examples': result}, 200

    if batch_raw:
        words = [word.strip().lower() for word in batch_raw.split(',') if word.strip()]
        result = {}
        for word in words:
            hits = books_vocabulary_loader_service.resolve_unified_examples(word)
            if hits:
                result[word] = hits
        return {'examples': result}, 200

    return {'error': 'Provide ?word=<word> or ?words=<word1,word2,...>'}, 400


def _empty_note(word: str) -> dict:
    return {'word': word, 'content': '', 'updated_at': None}


def _word_note_record(user_id: int, normalized_word: str):
    return word_note_repository.get_user_word_note(user_id, normalized_word)


def serialize_note_for_user(user, word: str, normalized_word: str) -> dict:
    if not user:
        return _empty_note(word)

    record = _word_note_record(user.id, normalized_word)
    if not record:
        return _empty_note(word)
    return record.to_dict()


def build_word_details_response(raw_word: str, current_user) -> tuple[dict, int]:
    word = str(raw_word or '').strip()
    if not word:
        return {'error': 'word is required'}, 400

    catalog_entry, changed = ensure_word_catalog_entry(word)
    if changed:
        word_catalog_repository.commit()

    normalized_word = normalize_word_key(word)
    resolved_phonetic = (
        phonetic_lookup_service.lookup_local_phonetic(word)
        or phonetic_lookup_service.resolve_phonetic(word, allow_remote=True)
    )
    if resolved_phonetic and catalog_entry.phonetic != resolved_phonetic:
        catalog_entry.phonetic = resolved_phonetic
        word_catalog_repository.commit()

    catalog_payload = catalog_entry.to_dict()
    examples = books_vocabulary_loader_service.resolve_unified_examples(
        word,
        fallback_examples=catalog_payload['examples'],
        limit=1,
    )
    return {
        'word': word,
        'phonetic': catalog_payload['phonetic'],
        'pos': catalog_payload['pos'],
        'definition': catalog_payload['definition'],
        'root': catalog_payload['root'],
        'english': catalog_payload['english'],
        'examples': examples,
        'derivatives': catalog_payload['derivatives'],
        'books': catalog_payload['books'],
        'note': serialize_note_for_user(current_user, word, normalized_word),
    }, 200
