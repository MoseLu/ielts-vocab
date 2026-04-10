from __future__ import annotations

from service_models.catalog_content_models import (
    WordDerivativeEntry,
    WordEnglishMeaning,
    WordExampleEntry,
    WordRootDetail,
)


def list_root_details():
    return WordRootDetail.query.all()


def list_english_meanings():
    return WordEnglishMeaning.query.all()


def list_example_entries():
    return WordExampleEntry.query.all()


def list_derivative_entries():
    return WordDerivativeEntry.query.all()


def get_root_detail(normalized_word: str):
    return WordRootDetail.query.filter_by(normalized_word=normalized_word).first()


def get_english_meaning(normalized_word: str):
    return WordEnglishMeaning.query.filter_by(normalized_word=normalized_word).first()


def list_derivatives(normalized_word: str):
    return WordDerivativeEntry.query.filter_by(normalized_base_word=normalized_word).order_by(
        WordDerivativeEntry.sort_order.asc(),
        WordDerivativeEntry.derivative_word.asc(),
    ).all()


def list_examples(normalized_word: str):
    return WordExampleEntry.query.filter_by(normalized_word=normalized_word).order_by(
        WordExampleEntry.sort_order.asc(),
        WordExampleEntry.id.asc(),
    ).all()
