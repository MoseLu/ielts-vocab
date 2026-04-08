from __future__ import annotations


VOCAB_BOOKS = [
    {
        'id': 'ielts_reading_premium',
        'title': '雅思阅读高频词汇',
        'description': '雅思阅读训练核心词汇，提升阅读理解能力',
        'icon': 'book-open',
        'color': '#7C3AED',
        'category': 'reading',
        'level': 'intermediate',
        'word_count': 3401,
        'file': 'ielts_reading_premium.json',
        'is_paid': True,
        'study_type': 'ielts',
        'has_chapters': True,
    },
    {
        'id': 'ielts_listening_premium',
        'title': '雅思听力高频词汇',
        'description': '雅思听力考试核心高频词汇，精选自听力真题',
        'icon': 'headphones',
        'color': '#2563EB',
        'category': 'listening',
        'level': 'intermediate',
        'word_count': 3910,
        'file': 'ielts_listening_premium.json',
        'is_paid': True,
        'study_type': 'ielts',
        'has_chapters': True,
    },
    {
        'id': 'ielts_comprehensive',
        'title': '雅思综合词汇5000+',
        'description': '雅思全面词汇库，覆盖听说读写全部场景',
        'icon': 'library',
        'color': '#EC4899',
        'category': 'comprehensive',
        'level': 'advanced',
        'word_count': 6260,
        'file': 'ielts_vocabulary_6260.csv',
        'study_type': 'ielts',
        'has_chapters': True,
    },
    {
        'id': 'ielts_ultimate',
        'title': '雅思终极词汇库',
        'description': '精选1938个雅思高频词汇',
        'icon': 'star',
        'color': '#F97316',
        'category': 'comprehensive',
        'level': 'advanced',
        'word_count': 1938,
        'file': 'ielts_vocabulary_ultimate.csv',
        'study_type': 'ielts',
        'has_chapters': True,
    },
    {
        'id': 'awl_academic',
        'title': 'AWL学术词汇表',
        'description': 'Academic Word List 570核心学术词汇，雅思学术类必备',
        'icon': 'graduation-cap',
        'color': '#8B5CF6',
        'category': 'academic',
        'level': 'advanced',
        'word_count': 570,
        'file': 'ielts_vocabulary_awl_extended.json',
        'study_type': 'ielts',
        'has_chapters': True,
    },
    {
        'id': 'ielts_9400_extended',
        'title': '雅思9400扩展词书',
        'description': '基于9400词表整理的扩展词库，已过滤明显缩写、专名与异常词条',
        'icon': 'library',
        'color': '#F97316',
        'category': 'comprehensive',
        'level': 'advanced',
        'word_count': 9248,
        'file': 'ielts_9400_extended.json',
        'study_type': 'ielts',
        'has_chapters': True,
    },
    {
        'id': 'ielts_confusable_match',
        'title': '雅思易混词辨析',
        'description': '自动抽取音近词与形近词，配合消消乐专项辨析',
        'icon': 'sparkles',
        'color': '#22C55E',
        'category': 'confusable',
        'level': 'advanced',
        'word_count': 2026,
        'file': 'ielts_confusable_match.json',
        'study_type': 'ielts',
        'has_chapters': True,
        'practice_mode': 'match',
    },
]


def list_vocab_books(book_ids: list[str] | tuple[str, ...] | set[str] | None = None) -> list[dict]:
    if book_ids is None:
        return VOCAB_BOOKS
    allowed_ids = {str(book_id) for book_id in book_ids if book_id}
    return [book for book in VOCAB_BOOKS if str(book.get('id')) in allowed_ids]


def get_vocab_book(book_id: str | None) -> dict | None:
    if not book_id:
        return None
    return next((book for book in VOCAB_BOOKS if str(book.get('id')) == str(book_id)), None)


def get_vocab_book_title_map() -> dict[str, str]:
    return {
        str(book['id']): str(book.get('title') or book['id'])
        for book in VOCAB_BOOKS
    }


def get_vocab_book_word_count_map() -> dict[str, int]:
    return {
        str(book['id']): max(0, int(book.get('word_count') or 0))
        for book in VOCAB_BOOKS
    }
