from __future__ import annotations

import re
from functools import lru_cache


@lru_cache(maxsize=1)
def _load_similarity_route_support():
    from platform_sdk.ai_similarity_application import get_global_vocab_pool, list_preset_listening_confusables
    from services.listening_confusables import rank_preset_listening_confusables

    return get_global_vocab_pool, list_preset_listening_confusables, rank_preset_listening_confusables


def _levenshtein(a: str, b: str) -> int:
    m, n = len(a), len(b)
    dp = list(range(n + 1))
    for i in range(1, m + 1):
        prev = dp[0]
        dp[0] = i
        for j in range(1, n + 1):
            tmp = dp[j]
            dp[j] = prev if a[i - 1] == b[j - 1] else 1 + min(prev, dp[j], dp[j - 1])
            prev = tmp
    return dp[n]


_IPA_STRIP = re.compile(r'[/\[\]ˈˌ.: ]')
_MEANING_POS_RE = re.compile(r'\b(?:n|v|vi|vt|adj|adv|prep|pron|conj|aux|int|num|art|a)\.\s*', re.IGNORECASE)


def _clean_meaning_fragment(value: str) -> str:
    return re.sub(
        r'\s+',
        ' ',
        _MEANING_POS_RE.sub(' ', (value or '')).replace('（', ' ').replace('）', ' ').replace('(', ' ').replace(')', ' '),
    ).strip()


def _normalize_meaning_text(value: str) -> str:
    text = _clean_meaning_fragment(value).lower()
    text = re.sub(r'[;；，,、/]', ' ', text)
    text = re.sub(r'[。！？]', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()


def _normalize_listening_token(token: str) -> str:
    if token.endswith('ies') and len(token) > 4:
        return f'{token[:-3]}y'
    if re.search(r'(?:ches|shes|xes|zes|ses|oes)$', token) and len(token) > 4:
        return token[:-2]
    if token.endswith('s') and len(token) > 3 and not re.search(r'(?:ss|us|is)$', token):
        return token[:-1]
    return token


def _normalize_listening_family_key(word: str | None, group_key: str | None = None) -> str:
    base = (group_key or word or '').strip().lower()
    if not base:
        return ''

    normalized = base
    normalized = re.sub(r"[’‘`]", "'", normalized)
    normalized = re.sub(r'[‐‑‒–—―]', '-', normalized)
    normalized = re.sub(r'^[\s"\'“”‘’.,!?;:()[\]{}]+', '', normalized)
    normalized = re.sub(r'[\s"\'“”‘’.,!?;:()[\]{}]+$', '', normalized)
    normalized = re.sub(r'\s+', ' ', normalized)
    normalized = re.sub(r'metres\b', 'meters', normalized)
    normalized = re.sub(r'metre\b', 'meter', normalized)
    normalized = re.sub(r'litres\b', 'liters', normalized)
    normalized = re.sub(r'litre\b', 'liter', normalized)
    normalized = re.sub(r'centres\b', 'centers', normalized)
    normalized = re.sub(r'centre\b', 'center', normalized)
    normalized = re.sub(r'theatres\b', 'theaters', normalized)
    normalized = re.sub(r'theatre\b', 'theater', normalized)

    tokens: list[str] = []
    for token in normalized.split(' '):
        parts = [_normalize_listening_token(part) for part in token.split('-')]
        tokens.append('-'.join(parts))
    return ' '.join(tokens).strip()


def _confusability_score(
    tw: str,
    tp: str,
    tpos: str,
    cw: str,
    cp: str,
    cpos: str,
) -> float:
    tw_l, cw_l = tw.lower(), cw.lower()
    score = 0.0

    if tpos and cpos and tpos == cpos:
        score += 2.0

    sd = _levenshtein(tw_l, cw_l)
    mx = max(len(tw_l), len(cw_l))
    if mx:
        score += (1 - sd / mx) * 5

    pfx = 0
    while pfx < len(tw_l) and pfx < len(cw_l) and tw_l[pfx] == cw_l[pfx]:
        pfx += 1
    score += min(pfx * 0.8, 3.0)

    sfx = 0
    while sfx < len(tw_l) and sfx < len(cw_l) and tw_l[-(sfx + 1)] == cw_l[-(sfx + 1)]:
        sfx += 1
    score += min(sfx * 0.5, 1.5)

    if abs(len(tw_l) - len(cw_l)) <= 2:
        score += 0.5

    if tp and cp:
        tp_s = _IPA_STRIP.sub('', tp).lower()
        cp_s = _IPA_STRIP.sub('', cp).lower()
        if tp_s and cp_s:
            pd = _levenshtein(tp_s, cp_s)
            mp = max(len(tp_s), len(cp_s))
            if mp:
                score += (1 - pd / mp) * 4

    return score


@ai_bp.route('/similar-words', methods=['GET'])
@token_required
def get_similar_words(current_user: User):
    del current_user
    (
        get_global_vocab_pool,
        list_preset_listening_confusables,
        rank_preset_listening_confusables,
    ) = _load_similarity_route_support()
    target_word = (request.args.get('word') or '').strip()
    if not target_word:
        return jsonify({'error': 'word is required'}), 400

    target_phonetic = request.args.get('phonetic', '')
    target_pos = request.args.get('pos', '')
    target_definition = request.args.get('definition', '')
    target_group_key = request.args.get('group_key', '')
    n = min(int(request.args.get('n', 10)), 20)

    pool = get_global_vocab_pool()
    tw_lower = target_word.lower()
    target_definition_norm = _normalize_meaning_text(target_definition)
    target_family_key = _normalize_listening_family_key(target_word, target_group_key)

    preset_results: list[dict] = []
    seen_preset_family_keys: set[str] = set()
    ranked_preset_words = rank_preset_listening_confusables(
        {
            'word': target_word,
            'phonetic': target_phonetic,
            'pos': target_pos,
            'definition': target_definition,
        },
        list_preset_listening_confusables(target_word, limit=n * 2),
    )
    for preset_word in ranked_preset_words:
        candidate_word = (preset_word.get('word') or '').strip()
        if not candidate_word or candidate_word.lower() == tw_lower:
            continue
        candidate_family_key = _normalize_listening_family_key(candidate_word, preset_word.get('group_key'))
        if target_family_key and candidate_family_key == target_family_key:
            continue
        if candidate_family_key and candidate_family_key in seen_preset_family_keys:
            continue
        if target_definition_norm and _normalize_meaning_text(preset_word.get('definition', '')) == target_definition_norm:
            continue
        if candidate_family_key:
            seen_preset_family_keys.add(candidate_family_key)
        preset_results.append(preset_word)
        if len(preset_results) >= n:
            break

    if preset_results:
        return jsonify({'words': preset_results})

    scored: list[tuple[float, str, dict]] = []
    for word_data in pool:
        candidate_word = (word_data.get('word') or '').strip()
        if not candidate_word:
            continue
        candidate_family_key = _normalize_listening_family_key(candidate_word, word_data.get('group_key'))
        if candidate_word.lower() == tw_lower:
            continue
        if target_family_key and candidate_family_key == target_family_key:
            continue
        if target_definition_norm and _normalize_meaning_text(word_data.get('definition', '')) == target_definition_norm:
            continue
        score = _confusability_score(
            target_word,
            target_phonetic,
            target_pos,
            candidate_word,
            word_data.get('phonetic', ''),
            word_data.get('pos', ''),
        )
        scored.append((score, candidate_family_key, word_data))

    scored.sort(key=lambda item: -item[0])
    results: list[dict] = []
    seen_family_keys: set[str] = set()
    for _, family_key, word_data in scored:
        if family_key and family_key in seen_family_keys:
            continue
        if family_key:
            seen_family_keys.add(family_key)
        results.append(word_data)
        if len(results) >= n:
            break
    return jsonify({'words': results})
