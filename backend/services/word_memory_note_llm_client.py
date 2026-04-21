from __future__ import annotations

import json
import re

from services.word_detail_llm_client import (
    DEFAULT_PROVIDER,
    _request_provider_messages,
    extract_json_block,
    request_plan,
)


def _normalize_memory_items(
    raw_payload,
    normalize_word,
    *,
    default_word: str | None = None,
) -> dict[str, dict]:
    if isinstance(raw_payload, dict):
        items = raw_payload.get('items') or raw_payload.get('results') or raw_payload.get('words')
        if items is None and (raw_payload.get('word') or default_word):
            single_item = dict(raw_payload)
            if default_word and not single_item.get('word'):
                single_item['word'] = default_word
            items = [single_item]
    elif isinstance(raw_payload, list):
        items = raw_payload
    else:
        items = []

    single_target = default_word if len(items or []) == 1 else None
    normalized_items = {}
    for item in items or []:
        if not isinstance(item, dict):
            continue
        word = item.get('word') or single_target
        key = normalize_word(word)
        if single_target and key != normalize_word(single_target):
            item = {**item, 'word': single_target}
            key = normalize_word(single_target)
        if not key:
            continue
        normalized_items[key] = item
    return normalized_items


def _build_seed_payload(word_seed: dict) -> dict:
    return {
        'word': word_seed['normalized_word'],
        'display_word': word_seed['display_word'],
        'phonetic': word_seed['phonetic'],
        'pos': word_seed['pos'],
        'cn_definitions': word_seed['definitions'],
        'examples': word_seed['examples'][:2],
        'is_phrase': bool(word_seed['is_phrase']),
        'book_ids': word_seed['book_ids'][:4],
    }


def _memory_system_prompt() -> str:
    return (
        '你是雅思词汇记忆编辑。请只返回合法 JSON，不要 markdown，不要解释。'
        '返回数组，顺序必须与输入一致，每个输入词都必须返回一个对象。'
        '每个对象必须包含 word、badge、text。'
        'word 必须原样返回输入里的小写 word。'
        'badge 只能是 谐音 或 联想。只有谐音自然顺口时才用 谐音，否则用 联想。'
        'text 必须是 1 句自然中文记忆提示，目标是帮助用户记住给定中文义。'
        'text 必须把词义自然落到画面、场景、谐音、弱拆词或对比串记里，长度控制在 12 到 60 个字左右。'
        'text 必须显式带出至少一个输入里的中文义关键词，不要只做宽泛改写。'
        '如果一个词有多个常见义，优先绑定最常用、最容易记住的那一个中文义。'
        '禁止只重复释义，禁止只返回原词，禁止只写词根词缀链，禁止 x+y、a + bit、ab + road 这类机械拆分。'
        '如果是短语或词组，必须用熟悉场景来记，严禁逐词硬拆。'
        '输出里不要包含额外字段。'
    )


def _build_messages(word_seeds: list[dict]) -> list[dict]:
    payload = [_build_seed_payload(seed) for seed in word_seeds]
    return [
        {'role': 'system', 'content': _memory_system_prompt()},
        {'role': 'user', 'content': json.dumps(payload, ensure_ascii=False)},
    ]


def _build_single_word_messages(word_seed: dict) -> list[dict]:
    return [
        {'role': 'system', 'content': _memory_system_prompt().replace('返回数组，顺序必须与输入一致，每个输入词都必须返回一个对象。', '请只返回一个合法 JSON 对象。')},
        {
            'role': 'user',
            'content': json.dumps(
                _build_seed_payload(word_seed),
                ensure_ascii=False,
            ),
        },
    ]


def _parse_single_word_text_fallback(raw_text: str, default_word: str) -> dict:
    text = str(raw_text or '').strip()
    text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s*```$', '', text).strip()
    lines = [
        line.strip().lstrip('-•* ').strip()
        for line in text.splitlines()
        if line.strip()
    ]
    candidate = ' '.join(lines).strip()
    if not candidate:
        raise ValueError('LLM returned empty text')

    badge = '谐音' if candidate.startswith('谐音') else '联想'
    candidate = re.sub(r'^(?:联想|谐音)\s*[：:]\s*', '', candidate).strip()
    if not candidate:
        raise ValueError('LLM returned empty text')

    return {
        'word': default_word,
        'badge': badge,
        'text': candidate,
    }


def request_memory_note_batch(
    word_seeds: list[dict],
    *,
    provider: str = DEFAULT_PROVIDER,
    model: str | None = None,
    fallback_provider: str | None = None,
    fallback_model: str | None = None,
    normalize_word,
) -> dict[str, dict]:
    single_word = word_seeds[0]['normalized_word'] if len(word_seeds) == 1 else None
    messages = (
        _build_single_word_messages(word_seeds[0])
        if single_word
        else _build_messages(word_seeds)
    )
    max_tokens = min(2400, max(500, 320 + (len(word_seeds) * 180)))
    errors = []

    for current_provider, current_model in request_plan(
        provider,
        model,
        fallback_provider,
        fallback_model,
    ):
        attempts = 2 if single_word else 1
        last_error = None
        for attempt in range(attempts):
            try:
                raw_text = _request_provider_messages(
                    messages,
                    provider=current_provider,
                    model=current_model,
                    max_tokens=max_tokens,
                )
                try:
                    parsed = json.loads(extract_json_block(raw_text))
                except ValueError:
                    if not single_word:
                        raise
                    parsed = _parse_single_word_text_fallback(raw_text, single_word)
                normalized_items = _normalize_memory_items(
                    parsed,
                    normalize_word,
                    default_word=single_word,
                )
                missing = [
                    seed['normalized_word']
                    for seed in word_seeds
                    if seed['normalized_word'] not in normalized_items
                ]
                if missing:
                    raise ValueError(f'LLM result missing words: {", ".join(missing)}')
                return normalized_items
            except Exception as exc:
                last_error = exc
                if attempt + 1 < attempts:
                    continue
        errors.append(f'{current_provider}/{current_model}: {last_error}')

    raise RuntimeError(' | '.join(errors))
