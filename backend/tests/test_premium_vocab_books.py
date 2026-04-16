import json
import re
from pathlib import Path

from services import books_registry_service
from services.premium_vocab_cleanup import normalize_premium_word


REPO_ROOT = Path(__file__).resolve().parents[2]
VOCAB_ROOT = REPO_ROOT / 'vocabulary_data'
TARGET_BOOKS = {
    'ielts_reading_premium': 'ielts_reading_premium.json',
    'ielts_listening_premium': 'ielts_listening_premium.json',
}
WORD_RE = re.compile(r"^[a-z]+(?:[-'][a-z]+|')*(?: [a-z]+(?:[-'][a-z]+|')*)*$")
FORBIDDEN_DEFINITION_TOKENS = (
    '人名',
    '地名',
    '州名',
    'abbr.',
    '缩写',
    '马萨诸塞州',
    '威斯康星州',
    '伊利诺伊州',
    '坦桑尼亚',
    '洛杉矶',
    '新南威尔士州',
    '西澳大利亚',
    '东非',
    '东南亚',
    '南非',
    '南美洲',
    '北美洲',
    '拉丁语系国家',
    '美国国家航空航天局',
    '莎士比亚',
    '奥林匹克运动会',
)
FORBIDDEN_WORDS = {'latin', 'olympic', 'great britain', 'northern ireland', 'hollywood'}


def _load_book_payload(filename: str) -> dict:
    return json.loads((VOCAB_ROOT / filename).read_text(encoding='utf-8'))


def _build_book_phonetic_map(filename: str) -> dict[str, str]:
    payload = _load_book_payload(filename)
    return {
        str(entry.get('word') or '').strip().lower(): str(entry.get('phonetic') or '').strip()
        for chapter in payload['chapters']
        for entry in chapter['words']
    }


def test_premium_books_have_synced_metadata_and_no_phrase_chapters():
    registry_count_map = books_registry_service.get_vocab_book_word_count_map()

    for book_id, filename in TARGET_BOOKS.items():
        payload = _load_book_payload(filename)
        chapters = payload['chapters']
        total_words = sum(len(chapter['words']) for chapter in chapters)

        assert payload['total_chapters'] == len(chapters)
        assert payload['total_words'] == total_words
        assert registry_count_map[book_id] == total_words
        assert all(chapter['word_count'] == len(chapter['words']) for chapter in chapters)


def test_premium_books_only_keep_clean_single_word_entries():
    for filename in TARGET_BOOKS.values():
        payload = _load_book_payload(filename)
        seen_words: set[str] = set()
        violations: list[str] = []

        for chapter in payload['chapters']:
            for entry in chapter['words']:
                word = str(entry.get('word') or '').strip()
                definition = str(entry.get('definition') or entry.get('translation') or '').strip()
                normalized = normalize_premium_word(word)

                if not word or word != normalized:
                    violations.append(f'{filename}:{chapter["title"]}:word-not-normalized:{word}')
                if not WORD_RE.fullmatch(word):
                    violations.append(f'{filename}:{chapter["title"]}:invalid-shape:{word}')
                if word in FORBIDDEN_WORDS:
                    violations.append(f'{filename}:{chapter["title"]}:blocked-word:{word}')
                if any(token in definition for token in FORBIDDEN_DEFINITION_TOKENS):
                    violations.append(f'{filename}:{chapter["title"]}:forbidden-definition:{word}')
                if word in seen_words:
                    violations.append(f'{filename}:{chapter["title"]}:duplicate:{word}')

                seen_words.add(word)

        assert violations == []


def test_known_premium_phonetic_regressions_stay_fixed():
    expected = {
        'ielts_listening_premium.json': {
            'arising': '/əˈraɪzɪŋ/',
            'elementary': '/ˌelɪˈmentəri/',
            'herbs': '/hɜːbz/',
            'history': '/ˈhɪstəri/',
            'increases': '/ɪnˈkriːsɪz/',
            'instruments': '/ˈɪnstrəmənts/',
            'quantities': '/ˈkwɒntɪtɪz/',
            'recruits': '/rɪˈkruːts/',
            'structures': '/ˈstrʌktʃəz/',
            'the amount of': '/ðiː əˈmaʊnt əv/',
            'visuals': '/ˈvɪʒuəlz/',
        },
        'ielts_reading_premium.json': {
            'abuse': '/əˈbjuːz/',
            'elementary': '/ˌelɪˈmentəri/',
            'history': '/ˈhɪstəri/',
            'instruments': '/ˈɪnstrəmənts/',
            'quantities': '/ˈkwɒntɪtɪz/',
            'stadiums': '/ˈsteɪdiəmz/',
            'the amount of': '/ðiː əˈmaʊnt əv/',
        },
    }
    for filename, cases in expected.items():
        phonetic_map = _build_book_phonetic_map(filename)
        for word, phonetic in cases.items():
            assert phonetic_map[word] == phonetic

    overrides = json.loads((VOCAB_ROOT / 'phonetic_overrides.json').read_text(encoding='utf-8'))
    for word, phonetic in {
        'abuse': '/əˈbjuːz/',
        'arising': '/əˈraɪzɪŋ/',
        'elementary': '/ˌelɪˈmentəri/',
        'herbs': '/hɜːbz/',
        'history': '/ˈhɪstəri/',
        'increases': '/ɪnˈkriːsɪz/',
        'instruments': '/ˈɪnstrəmənts/',
        'quantities': '/ˈkwɒntɪtɪz/',
        'recruits': '/rɪˈkruːts/',
        'stadiums': '/ˈsteɪdiəmz/',
        'structures': '/ˈstrʌktʃəz/',
        'the amount of': '/ðiː əˈmaʊnt əv/',
        'visuals': '/ˈvɪʒuəlz/',
    }.items():
        assert overrides[word] == phonetic
