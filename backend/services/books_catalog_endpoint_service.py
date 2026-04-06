from __future__ import annotations

from importlib import import_module


def _books_module():
    return import_module('routes.books')


def build_categories_response():
    books = _books_module()
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
    categories = list(set(book['category'] for book in books.VOCAB_BOOKS))
    return {
        'categories': [
            {'id': category, 'name': category_names.get(category, category)}
            for category in categories
        ]
    }, 200


def build_levels_response():
    books = _books_module()
    level_names = {
        'beginner': '初级',
        'intermediate': '中级',
        'advanced': '高级',
    }
    levels = list(set(book['level'] for book in books.VOCAB_BOOKS))
    return {
        'levels': [
            {'id': level, 'name': level_names.get(level, level)}
            for level in levels
        ]
    }, 200


def build_books_stats_response():
    books = _books_module()
    total_words = sum(book['word_count'] for book in books.VOCAB_BOOKS)
    return {
        'total_books': len(books.VOCAB_BOOKS),
        'total_words': total_words,
        'categories': len(set(book['category'] for book in books.VOCAB_BOOKS)),
    }, 200
