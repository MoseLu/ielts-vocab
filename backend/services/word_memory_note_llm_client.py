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
        'badge 必须从 助记、联想、词根词缀、辨析、串记、扩展、谐音、词源、口诀 中选一个。'
        '请先根据证据选择最适合的单一类型，不要强行联想；只有谐音自然顺口时才用 谐音。'
        '优先级：辨析用于近义/易混词差异；扩展用于同根、派生、复合词或固定搭配；词根词缀只用于真实常见词根；串记用于形近拼写；谐音只能作最后选择。'
        '类型规则：词根词缀要写真实前缀/词根/后缀并落回中文义；扩展要给2到5个同族词、派生词或固定搭配；'
        '串记要排列形近/同根近形词并点出差异；辨析要比较近义词的使用边界；联想要有词形、画面、动作或考试场景钩子；'
        '谐音必须自然顺口且一句话绑定词义；助记用于无可靠词根时的短场景或动作记忆。'
        '词根词缀只能拆常见且有把握的部分；不要把任意尾部硬说成后缀，例如不确定时只写 cert 表确定，不要补 -ain 这类假后缀。'
        '禁止把没有真实语义关系的形近词硬连，例如“加/少一个字母就是某义”；只有 quit/quiet 这类教学常见易混对比才可串记。'
        '参考风格：unemployment 可写 un 表否定，employ 是雇佣，合起来是不被雇佣的失业状态；'
        'extension 可写 extend 是延伸，extension 是延伸出的部分，也可指延期或电话分机；'
        'biography 可串 biography 写人的一生，biology 学生命本身，geography 写地理；'
        'gigantic 可辨析 gigantic 强调体积巨大，vast 偏空间辽阔，massive 偏规模和重量；'
        'certain 必须只写 cert 表确定，certificate 是证明，certain 就是证据够了心里确定；禁止写 -ain 后缀。'
        'text 必须像词典笔记一样短、准、有章法，可含 2 到 5 个相关词，但每个相关词都要服务给定中文义。'
        '每条 text 都必须有真实可回忆的钩子：真实词根词缀、形近对比、词族扩展、固定搭配、考试场景画面或自然串记至少一种。'
        '多义词要覆盖或点明核心义群，不得把 mate 这类词只写成单一偏义。'
        '禁止使用拗口生造音译、伪词根、假拆分或编造人名地名；不确定词根时改用例句、扩展、辨析或形近串记。'
        '禁止低俗、暴力、自伤画面；除非释义本身包含死亡、杀死、致命等义，不要使用死、杀、尸、坟等刺激词。'
        'text 必须是 1 到 2 句自然中文记忆提示，目标是帮助用户记住给定中文义。'
        'text 必须把词义自然落到例句语境、真实词根、扩展词族、形近串记、自然谐音或近义辨析里，长度控制在 12 到 90 个字左右。'
        'text 必须显式带出至少一个输入里的中文义关键词，不要只做宽泛改写。'
        '如果一个词有多个常见义，优先绑定最常用、最容易记住的那一个中文义。'
        '禁止只重复释义，禁止只返回原词，禁止只写没有中文解释的词根词缀链，禁止 a + bit、ab + road 这类伪拆分。'
        '禁止模板句：先抓核心义、放回句子判断、核心义仍是、就是某某、表示某某、记住它常落在某语境。'
        '派生词、复数词、现在分词不能只写“是某词的复数/现在分词”，必须说明词义变化或使用场景。'
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
    max_tokens = min(2048, max(500, 320 + (len(word_seeds) * 180)))
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
