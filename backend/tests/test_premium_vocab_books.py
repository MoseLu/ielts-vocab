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
MEMORY_BADGES = {'助记', '联想', '词根词缀', '辨析', '串记', '扩展', '谐音', '词源', '口诀', '派生'}
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


def _premium_word_union() -> dict[str, set[str]]:
    words: dict[str, set[str]] = {}
    for book_id, filename in TARGET_BOOKS.items():
        payload = _load_book_payload(filename)
        for chapter in payload['chapters']:
            for entry in chapter['words']:
                normalized = normalize_premium_word(entry.get('word'))
                words.setdefault(normalized, set()).add(book_id)
    return words


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


def test_premium_word_mnemonics_cover_paid_book_union():
    payload = json.loads((VOCAB_ROOT / 'premium_word_mnemonics.json').read_text(encoding='utf-8'))
    expected_words = _premium_word_union()
    items = payload.get('items') or {}
    violations: list[str] = []

    if set(payload.get('book_ids') or []) != set(TARGET_BOOKS):
        violations.append('manifest-book-ids')
    if payload.get('manifest_version') != 1:
        violations.append('manifest-version')
    if set(items) != set(expected_words):
        missing = sorted(set(expected_words) - set(items))[:20]
        stale = sorted(set(items) - set(expected_words))[:20]
        violations.append(f'word-set mismatch missing={missing} stale={stale}')

    for word, book_ids in expected_words.items():
        item = items.get(word) or {}
        text = str(item.get('text') or '').strip()
        if item.get('word') != word:
            violations.append(f'{word}:word')
        if item.get('badge') not in MEMORY_BADGES:
            violations.append(f'{word}:badge')
        if not text or not re.search(r'[\u4e00-\u9fff]', text):
            violations.append(f'{word}:text')
        if set(item.get('book_ids') or []) != book_ids:
            violations.append(f'{word}:book_ids')
        if item.get('source') != 'premium_word_mnemonics':
            violations.append(f'{word}:source')

    assert violations == []


def test_premium_word_mnemonic_quality_regressions_stay_fixed():
    payload = json.loads((VOCAB_ROOT / 'premium_word_mnemonics.json').read_text(encoding='utf-8'))
    items = payload.get('items') or {}

    expected_text = {
        'mate': 'mate 核心是“配在一起”：人是伙伴/伴侣，动物是交配；workmate、schoolmate、teammate 都是同伴。',
        'demographic': 'demo 表“人群”，graphic 表“图表/描述”，合起来就是人口统计的、人口的。',
        'secrete': 'secret 是秘密，secrete 可记“把东西藏起来”；在生物语境中是腺体分泌液体。',
        'accommodation': 'accommodate 是“容纳/提供住宿”，accommodation 就是住处或住宿安排。',
        'have a look': 'have a look 是固定口语表达，意思是“看一下”。',
        'quit': 'quit 比 quiet 少一个 e，e 退出队伍，记“离开；停止；辞职”。',
        'quiz': 'quiz 常出现在课堂或节目语境，指知识竞赛或小测验。',
        'quiet': 'quiet 比 quit 多一个 e，像嘘声拉长让环境安静下来，记“安静的”。',
        'quick': 'quick 和 quit/quiet 同属 qu 开头易混词，quick 只记速度“快的；迅速的”。',
        'quote': 'quote 作动词是引用或报价，作名词是引文或报价；阅读中看价格还是文字出处。',
        'in a sense': 'in a sense 是固定表达，意思是“在某种意义上；从某种角度说”。',
        'universe': 'uni 表“一”，vers 有“转成整体”的线索；universe 是万物合成的整体，记“宇宙”。',
    }

    assert {
        word: (items.get(word) or {}).get('text')
        for word in expected_text
    } == expected_text


def test_premium_word_mnemonics_avoid_known_low_quality_patterns():
    payload = json.loads((VOCAB_ROOT / 'premium_word_mnemonics.json').read_text(encoding='utf-8'))
    items = payload.get('items') or {}
    bad_pattern = re.compile(
        r'阿康|阿不|阿得|阿瑞|阿瓦|阿太|不斯特|飞扣死|亏特|'
        r'一妈急死|大拜死|砍破|哈夫 阿 路克|连体婴|耳光|屎|撒尿|'
        r'派特|推下楼梯|moro\(人\)|crete 意为制造|de\(向下\)\+moro|bri-像|grave\(坟墓\)|'
        r'发音像|音似|听起来像|常见变体|词形变体|核心词义|'
        r'按语境确定含义|放进真实场景里记|先抓核心义|放回句子判断|核心义仍是|记住它常落在|'
        r'未来去宇宙|去宇宙.*上大学|上大学.*普遍|'
        r'\ba\s*[+＋]\s*bit\b|\bab\s*[+＋]\s*road\b|'
        r'[A-Za-z]+\([^)]{1,20}\)\s*[+＋]|[A-Za-z]+\s*[-–—]\s*像|'
        r'\b[A-Za-z]{1,6}-像|[-–—]>|->|→'
    )
    violations = [
        f'{word}:{item.get("text")}'
        for word, item in items.items()
        if bad_pattern.search(str(item.get('text') or ''))
    ]

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
        'button': '/ˈbʌtən/',
        'elementary': '/ˌelɪˈmentəri/',
        'herbs': '/hɜːbz/',
        'history': '/ˈhɪstəri/',
        'increases': '/ɪnˈkriːsɪz/',
        'instruments': '/ˈɪnstrəmənts/',
        'quantities': '/ˈkwɒntɪtɪz/',
        'recruits': '/rɪˈkruːts/',
        'refractory': '/ɹɪˈfɹæk.təɹ.i/',
        'stadiums': '/ˈsteɪdiəmz/',
        'structures': '/ˈstrʌktʃəz/',
        'the amount of': '/ðiː əˈmaʊnt əv/',
        'visuals': '/ˈvɪʒuəlz/',
    }.items():
        assert overrides[word] == phonetic
