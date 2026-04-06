from __future__ import annotations

from importlib import import_module


def _books_module():
    return import_module('routes.books')


def is_confusable_match_book(book_id: str) -> bool:
    books = _books_module()
    return str(book_id) == books.CONFUSABLE_MATCH_BOOK_ID


def build_confusable_custom_book_id(user_id: int) -> str:
    books = _books_module()
    return f'{books.CONFUSABLE_CUSTOM_BOOK_PREFIX}_{user_id}'


def resolve_optional_current_user():
    books = _books_module()
    token = books._extract_token()
    if not token:
        return None

    try:
        payload = books._decode_token(token)
    except Exception:
        return None

    if payload.get('type') != 'access':
        return None

    user_id = payload.get('user_id')
    if user_id is None:
        return None

    return books.User.query.get(user_id)


def _normalize_lookup_word_key(value) -> str:
    if not isinstance(value, str):
        return ''
    return value.strip().lower()


def _score_lookup_candidate(word_entry: dict, source_priority: int) -> tuple[int, int, int]:
    definition = (word_entry.get('definition') or '').strip()
    phonetic = (word_entry.get('phonetic') or '').strip()
    pos = (word_entry.get('pos') or '').strip()
    completeness = (3 if definition else 0) + (2 if phonetic else 0) + (1 if pos else 0)
    definition_length = min(len(definition), 200)
    return completeness, -source_priority, definition_length


def build_confusable_lookup() -> dict[str, dict]:
    books = _books_module()
    cached_lookup = getattr(books, '_confusable_lookup_cache', None)
    if isinstance(cached_lookup, dict):
        return cached_lookup

    lookup = {}
    for source_priority, book_id in enumerate(books.CONFUSABLE_LOOKUP_SOURCE_IDS):
        words = books.load_book_vocabulary(book_id) or []
        for word_entry in words:
            key = _normalize_lookup_word_key(word_entry.get('word'))
            if not key:
                continue

            candidate = {
                'word': (word_entry.get('word') or '').strip() or key,
                'phonetic': (word_entry.get('phonetic') or '').strip(),
                'pos': (word_entry.get('pos') or '').strip(),
                'definition': (word_entry.get('definition') or '').strip(),
            }
            candidate['_score'] = _score_lookup_candidate(candidate, source_priority)
            existing = lookup.get(key)
            if existing is None or candidate['_score'] > existing['_score']:
                lookup[key] = candidate

    for key, override in books.CONFUSABLE_LOOKUP_OVERRIDES.items():
        candidate = {
            'word': (override.get('word') or '').strip() or key,
            'phonetic': (override.get('phonetic') or '').strip(),
            'pos': (override.get('pos') or '').strip(),
            'definition': (override.get('definition') or '').strip(),
        }
        candidate['_score'] = _score_lookup_candidate(candidate, -1)
        existing = lookup.get(key)
        if existing is None or candidate['_score'] > existing['_score']:
            lookup[key] = candidate

    books._confusable_lookup_cache = lookup
    return lookup


def normalize_confusable_custom_groups(raw_groups) -> list[list[str]]:
    books = _books_module()
    if not isinstance(raw_groups, list) or not raw_groups:
        raise ValueError('请至少输入一组易混词')
    if len(raw_groups) > books.CONFUSABLE_CUSTOM_MAX_GROUPS:
        raise ValueError(f'一次最多创建 {books.CONFUSABLE_CUSTOM_MAX_GROUPS} 组易混词')

    groups = []
    for index, raw_group in enumerate(raw_groups, start=1):
        if isinstance(raw_group, str):
            tokens = books.CONFUSABLE_WORD_TOKEN_RE.findall(raw_group)
        elif isinstance(raw_group, list):
            tokens = []
            for item in raw_group:
                if not isinstance(item, str):
                    continue
                tokens.extend(books.CONFUSABLE_WORD_TOKEN_RE.findall(item))
        else:
            tokens = []

        unique_words = []
        seen = set()
        for token in tokens:
            normalized = _normalize_lookup_word_key(token)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            unique_words.append(normalized)

        if len(unique_words) < 2:
            raise ValueError(f'第 {index} 组至少需要 2 个不同单词')
        if len(unique_words) > books.CONFUSABLE_CUSTOM_MAX_WORDS_PER_GROUP:
            raise ValueError(
                f'第 {index} 组最多支持 {books.CONFUSABLE_CUSTOM_MAX_WORDS_PER_GROUP} 个单词'
            )
        groups.append(unique_words)

    return groups


def resolve_confusable_group_words(groups: list[list[str]]) -> tuple[list[list[dict]], list[str]]:
    lookup = build_confusable_lookup()
    resolved_groups = []
    missing_words = set()

    for group in groups:
        resolved_words = []
        for word in group:
            candidate = lookup.get(word)
            if not candidate or not candidate.get('definition') or not candidate.get('phonetic'):
                missing_words.add(word)
                continue

            resolved_words.append({
                'word': candidate['word'],
                'phonetic': candidate['phonetic'],
                'pos': candidate.get('pos') or 'n.',
                'definition': candidate['definition'],
            })

        if resolved_words:
            resolved_groups.append(resolved_words)

    return resolved_groups, sorted(missing_words)


def get_confusable_custom_book(user_id: int, create: bool = False):
    books = _books_module()
    book_id = build_confusable_custom_book_id(user_id)
    book = books.CustomBook.query.filter_by(id=book_id, user_id=user_id).first()
    if book or not create:
        return book

    book = books.CustomBook(
        id=book_id,
        user_id=user_id,
        title='我的易混辨析',
        description='用户手动创建的易混词组合',
        word_count=0,
    )
    books.db.session.add(book)
    return book


def get_confusable_custom_word_count(user_id: int | None) -> int:
    if not user_id:
        return 0
    book = get_confusable_custom_book(user_id)
    return int(book.word_count or 0) if book else 0


def list_confusable_custom_chapters(user_id: int | None) -> list[dict]:
    if not user_id:
        return []

    book = get_confusable_custom_book(user_id)
    if not book:
        return []

    chapters = []
    for chapter in book.chapters:
        try:
            chapter_id = int(str(chapter.id))
        except (TypeError, ValueError):
            continue
        chapters.append({
            'id': chapter_id,
            'title': chapter.title,
            'word_count': int(chapter.word_count or len(chapter.words)),
            'group_count': 1,
            'is_custom': True,
        })
    return chapters


def get_confusable_custom_chapter(user_id: int | None, chapter_id: int):
    if not user_id:
        return None

    books = _books_module()
    book_id = build_confusable_custom_book_id(user_id)
    return books.CustomBookChapter.query.filter_by(book_id=book_id, id=str(chapter_id)).first()


def next_confusable_custom_chapter_id(book) -> int:
    books = _books_module()
    numeric_ids = []
    for chapter in book.chapters:
        try:
            numeric_ids.append(int(str(chapter.id)))
        except (TypeError, ValueError):
            continue
    return max([books.CONFUSABLE_CUSTOM_CHAPTER_OFFSET, *numeric_ids]) + 1


def build_confusable_custom_chapter_title(words: list[str], sequence: int) -> str:
    preview = ' / '.join(words[:3])
    if len(words) > 3:
        preview += ' / ...'
    return f'自定义易混组 {sequence:02d} · {preview}'


def serialize_confusable_custom_words(chapter) -> list[dict]:
    group_key = f'custom-{chapter.id}'
    return [
        {
            'word': (word.word or '').strip(),
            'phonetic': (word.phonetic or '').strip(),
            'pos': (word.pos or 'n.').strip() or 'n.',
            'definition': (word.definition or '').strip(),
            'group_key': group_key,
        }
        for word in chapter.words
        if (word.word or '').strip()
    ]


def merge_confusable_custom_chapters(chapters_data: dict, user_id: int | None) -> dict:
    custom_chapters = list_confusable_custom_chapters(user_id)
    if not custom_chapters:
        return chapters_data

    return {
        'total_chapters': int(chapters_data.get('total_chapters') or 0) + len(custom_chapters),
        'total_words': int(chapters_data.get('total_words') or 0) + sum(
            int(chapter.get('word_count') or 0) for chapter in custom_chapters
        ),
        'total_groups': int(chapters_data.get('total_groups') or 0) + sum(
            int(chapter.get('group_count') or 0) for chapter in custom_chapters
        ),
        'chapters': [*(chapters_data.get('chapters') or []), *custom_chapters],
    }


def augment_book_for_user(book: dict, user_id: int | None) -> dict:
    books = _books_module()
    book_data = dict(book)
    if is_confusable_match_book(book_data.get('id')):
        if user_id:
            book_data['word_count'] = int(book_data.get('word_count') or 0) + get_confusable_custom_word_count(user_id)
        book_data['chapter_count'] = books._get_book_chapter_count(book_data.get('id'), user_id=user_id)
        book_data['group_count'] = books._get_book_group_count(book_data.get('id'), user_id=user_id)
    return book_data
