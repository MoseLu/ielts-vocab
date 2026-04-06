from __future__ import annotations

import re


_WORD_DETAIL_PREFIXES = [
    ('under', '常表示“在下方、不足”'),
    ('inter', '常表示“在……之间、相互”'),
    ('trans', '常表示“跨越、转移”'),
    ('super', '常表示“超出、在上”'),
    ('anti', '常表示“反对、抵抗”'),
    ('post', '常表示“之后”'),
    ('over', '常表示“过度、在上方”'),
    ('fore', '常表示“预先、在前”'),
    ('pre', '常表示“在前、预先”'),
    ('sub', '常表示“在下、次级”'),
    ('mid', '常表示“中间”'),
    ('out', '常表示“向外、超过”'),
    ('non', '常表示“非、不”'),
    ('mis', '常表示“错误地”'),
    ('dis', '常表示“否定、分离”'),
    ('re', '常表示“再次、回到”'),
    ('de', '常表示“向下、去除”'),
    ('un', '常表示“否定”'),
    ('im', '常表示“否定或进入”'),
    ('in', '常表示“进入或否定”'),
]

_WORD_DETAIL_SUFFIXES = [
    ('ation', '常表示“动作、过程或结果”'),
    ('ition', '常表示“动作、状态”'),
    ('ingly', '常表示“以……方式地”'),
    ('ment', '常表示“结果、行为或事物”'),
    ('ness', '常表示“性质、状态”'),
    ('able', '常表示“能够……的”'),
    ('ible', '常表示“能够……的”'),
    ('tion', '常表示“行为、名词化结果”'),
    ('sion', '常表示“行为、状态”'),
    ('ship', '常表示“身份、关系、状态”'),
    ('less', '常表示“没有……”'),
    ('ward', '常表示“朝向……”'),
    ('wise', '常表示“以……方式、在……方面”'),
    ('ally', '常表示“以……方式地”'),
    ('ical', '常表示“……相关的”'),
    ('ous', '常表示“具有……性质的”'),
    ('ive', '常表示“具有……倾向的”'),
    ('ing', '常表示“进行中”或构成动名词'),
    ('est', '常表示“最高级”'),
    ('ism', '常表示“主义、现象”'),
    ('ist', '常表示“从事某事的人”'),
    ('ity', '常表示“性质、状态”'),
    ('ful', '常表示“充满……”'),
    ('age', '常表示“集合、状态、费用”'),
    ('ery', '常表示“场所、集合”'),
    ('ory', '常表示“具有……性质的”'),
    ('ance', '常表示“状态、行为”'),
    ('ence', '常表示“状态、性质”'),
    ('ily', '常表示“以……方式地”'),
    ('ed', '常表示“已完成、过去式”'),
    ('er', '常表示“人、物或比较级”'),
    ('or', '常表示“人、物”'),
    ('al', '常表示“……相关的”'),
    ('ly', '常表示“以……方式地”'),
    ('ty', '常表示“性质、状态”'),
    ('s', '常表示“复数或第三人称单数”'),
]


def _normalize_word_key(value) -> str:
    if not isinstance(value, str):
        return ''
    return value.strip().lower()


def _match_affix(word: str, affixes: list[tuple[str, str]], kind: str):
    for text, meaning in affixes:
        if kind == 'prefix' and word.startswith(text) and len(word) - len(text) >= 3:
            return text, meaning
        if kind == 'suffix' and word.endswith(text) and len(word) - len(text) >= 3:
            return text, meaning
    return None


def build_default_root_payload(word: str) -> dict:
    normalized = _normalize_word_key(word)
    if not normalized:
        return {'segments': [], 'summary': '暂无可解析的词形信息。'}

    prefix = _match_affix(normalized, _WORD_DETAIL_PREFIXES, 'prefix')
    without_prefix = normalized[len(prefix[0]):] if prefix else normalized
    suffix = _match_affix(without_prefix, _WORD_DETAIL_SUFFIXES, 'suffix')
    root = without_prefix[:-len(suffix[0])] if suffix else without_prefix
    root_text = root or normalized

    segments = []
    if prefix:
        segments.append({'kind': '前缀', 'text': prefix[0], 'meaning': prefix[1]})
    segments.append({
        'kind': '词根',
        'text': root_text,
        'meaning': '建议把这部分当作核心词形来记' if prefix or suffix else '当前词形本身就是核心记忆单元',
    })
    if suffix:
        segments.append({'kind': '后缀', 'text': suffix[0], 'meaning': suffix[1]})

    if not prefix and not suffix:
        summary = f'当前没有命中常见前后缀，可以直接把 {normalized} 作为核心词形记忆。'
    else:
        parts = ' + '.join(segment['text'] for segment in segments)
        summary = f'可以按“{parts}”来拆分记忆，先抓住词根，再看前后缀补充的方向。'

    return {'segments': segments, 'summary': summary}


def _should_try_double_final_consonant(word: str) -> bool:
    return (
        len(word) >= 3
        and len(re.findall(r'[aeiouy]+', word)) == 1
        and bool(re.fullmatch(r'[bcdfghjklmnpqrstvwxyz]', word[-1]))
        and not word.endswith(('w', 'x', 'y', 'e'))
    )


def generate_derivative_candidates(word: str) -> list[str]:
    normalized = _normalize_word_key(word)
    if not normalized:
        return []

    candidates = []

    def add(candidate: str) -> None:
        if candidate and candidate != normalized and candidate not in candidates:
            candidates.append(candidate)

    if re.search(r'(s|x|z|ch|sh)$', normalized):
        add(f'{normalized}es')
    elif re.search(r'[^aeiou]y$', normalized):
        add(f'{normalized[:-1]}ies')
        add(f'{normalized[:-1]}ied')
    else:
        add(f'{normalized}s')

    if normalized.endswith('e'):
        add(f'{normalized[:-1]}ing')
        add(f'{normalized}r')
        add(f'{normalized}d')
    elif _should_try_double_final_consonant(normalized):
        last_letter = normalized[-1]
        add(f'{normalized}{last_letter}ing')
        add(f'{normalized}{last_letter}er')
        add(f'{normalized}{last_letter}ed')
    else:
        add(f'{normalized}ing')
        add(f'{normalized}er')
        add(f'{normalized}ed')

    for suffix in ('ly', 'ness', 'ment', 'able', 'al', 'ity'):
        add(f'{normalized}{suffix}')

    return candidates[:10]
