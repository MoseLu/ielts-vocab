HIGH_VALUE_EXTENSION_SUFFIXES = (
    "s",
    "es",
    "ed",
    "ing",
    "ly",
    "al",
    "ally",
    "ment",
    "er",
    "ers",
    "or",
    "ors",
)


def _surface_base_forms(word: str) -> set[str]:
    normalized = word.lower()
    forms = {normalized}

    if normalized.endswith("ies") and len(normalized) > 5:
        forms.add(normalized[:-3] + "y")
    if normalized.endswith("es") and len(normalized) > 4:
        forms.add(normalized[:-2])
    if normalized.endswith("s") and len(normalized) > 4 and not normalized.endswith(("ss", "us", "is")):
        forms.add(normalized[:-1])
    if normalized.endswith("ing") and len(normalized) > 6:
        stem = normalized[:-3]
        forms.update({stem, stem + "e"})
        if re.search(r"([bcdfghjklmnpqrstvwxyz])\1$", stem):
            forms.add(stem[:-1])
    if normalized.endswith("ed") and len(normalized) > 5:
        stem = normalized[:-2]
        forms.update({stem, stem + "e"})
        if re.search(r"([bcdfghjklmnpqrstvwxyz])\1$", stem):
            forms.add(stem[:-1])
    if normalized.endswith("ly") and len(normalized) > 5:
        forms.add(normalized[:-2])
    if normalized.endswith("ally") and len(normalized) > 7:
        forms.update({normalized[:-2], normalized[:-4]})
    if normalized.endswith("al") and len(normalized) > 5:
        forms.add(normalized[:-2])
    if normalized.endswith("ment") and len(normalized) > 7:
        forms.add(normalized[:-4])

    return {form for form in forms if len(form) >= 3}


def _is_low_value_derivation_pair(left_word: str, right_word: str) -> bool:
    left = left_word.lower()
    right = right_word.lower()
    if left == right:
        return True

    if left in _surface_base_forms(right) or right in _surface_base_forms(left):
        return True

    shorter, longer = sorted((left, right), key=len)
    if len(shorter) < 4:
        return False

    if longer.startswith(shorter):
        remainder = longer[len(shorter):]
        if remainder in HIGH_VALUE_EXTENSION_SUFFIXES:
            return True

    if shorter.endswith("e") and longer.startswith(shorter[:-1]):
        remainder = longer[len(shorter) - 1 :]
        if remainder in {"ing", "ed", "er", "ers"}:
            return True

    return False


def _consonant_signature(word: str) -> str:
    letters = re.sub(r"[^a-z]", "", word.lower())
    signature = "".join(char for char in letters if char not in "aeiou")
    return re.sub(r"(.)\1+", r"\1", signature)


def _phrase_tokens(word: str) -> list[str]:
    return [token for token in re.split(r"[\s-]+", word.lower()) if token]


def _has_shared_phrase_frame(target: WordEntry, candidate: WordEntry) -> bool:
    target_tokens = _phrase_tokens(target.word)
    candidate_tokens = _phrase_tokens(candidate.word)
    if not target_tokens or not candidate_tokens:
        return False
    if len(target_tokens) != len(candidate_tokens):
        return False

    for index, (left, right) in enumerate(zip(target_tokens, candidate_tokens)):
        if left == right:
            return True
        if index in (0, len(target_tokens) - 1) and left[:3] == right[:3]:
            return True
    return False


def _high_value_listening_candidate_score(target: WordEntry, candidate: WordEntry) -> float:
    score = listening_confusability_score(target, candidate)
    score += word_similarity(_consonant_signature(target.word), _consonant_signature(candidate.word)) * 20
    score += min(common_prefix_length(target.word, candidate.word), 4) * 4
    score += min(common_suffix_length(target.word, candidate.word), 3) * 2
    if _has_shared_phrase_frame(target, candidate):
        score += 12
    return score


def _is_high_value_listening_candidate(target: WordEntry, candidate: WordEntry) -> bool:
    if are_same_lexeme(target, candidate):
        return False
    if _is_low_value_derivation_pair(target.word, candidate.word):
        return False

    word_ratio = word_similarity(target.word, candidate.word)
    phonetic_ratio = phonetic_similarity(target, candidate)
    prefix_length = common_prefix_length(target.word, candidate.word)
    suffix_length = common_suffix_length(target.word, candidate.word)
    length_delta = abs(len(target.word) - len(candidate.word))
    consonant_ratio = word_similarity(
        _consonant_signature(target.word),
        _consonant_signature(candidate.word),
    )

    target_tokens = _phrase_tokens(target.word)
    candidate_tokens = _phrase_tokens(candidate.word)
    if len(target_tokens) > 1 or len(candidate_tokens) > 1:
        return (
            len(target_tokens) == len(candidate_tokens)
            and (_has_shared_phrase_frame(target, candidate) or phonetic_ratio >= 0.90)
            and (word_ratio >= 0.42 or phonetic_ratio >= 0.82 or consonant_ratio >= 0.55)
        )

    if prefix_length >= 3 and length_delta <= 4 and (word_ratio >= 0.55 or consonant_ratio >= 0.62):
        return True
    if phonetic_ratio >= 0.88 and length_delta <= 3 and (
        prefix_length >= 2 or suffix_length >= 2 or consonant_ratio >= 0.56
    ):
        return True
    if consonant_ratio >= 0.74 and word_ratio >= 0.58 and length_delta <= 3:
        return True
    return False


def _load_priority_group_words() -> list[list[str]]:
    if not PRIORITY_GROUPS_PATH.exists():
        return []

    try:
        payload = json.loads(PRIORITY_GROUPS_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"Warning: could not load confusable priority groups: {exc}")
        return []

    groups: list[list[str]] = []
    for raw_group in payload.get("groups", []):
        raw_words = raw_group.get("words", []) if isinstance(raw_group, dict) else raw_group
        if not isinstance(raw_words, list):
            continue

        normalized_words: list[str] = []
        seen_words: set[str] = set()
        for raw_word in raw_words:
            normalized_word = clean_word_text(str(raw_word or ""))
            if not normalized_word or normalized_word in seen_words:
                continue
            seen_words.add(normalized_word)
            normalized_words.append(normalized_word)

        if len(normalized_words) >= 2:
            groups.append(normalized_words)

    return groups


def _build_priority_group_candidate_map(entries_by_word: dict[str, WordEntry]) -> dict[str, list[WordEntry]]:
    lookup: dict[str, list[WordEntry]] = {}

    for group_words in _load_priority_group_words():
        resolved_entries = [entries_by_word[word] for word in group_words if word in entries_by_word]
        if len(resolved_entries) < 2:
            continue

        for target in resolved_entries:
            ranked_peers = sorted(
                [
                    candidate for candidate in resolved_entries
                    if candidate.word != target.word
                    and not _is_low_value_derivation_pair(target.word, candidate.word)
                ],
                key=lambda candidate: _high_value_listening_candidate_score(target, candidate),
                reverse=True,
            )
            if ranked_peers:
                lookup[target.word] = ranked_peers

    return lookup


def build_high_value_listening_presets(
    entries: list[WordEntry],
    candidate_limit: int,
) -> dict[str, list[dict[str, str]]]:
    entries_by_word = {entry.word: entry for entry in entries}
    buckets = build_listening_candidate_buckets(entries)
    priority_candidate_map = _build_priority_group_candidate_map(entries_by_word)
    presets: dict[str, list[dict[str, str]]] = {}

    for entry in entries:
        selected: list[WordEntry] = []
        seen_words: set[str] = set()

        def add_candidate(candidate: WordEntry) -> None:
            if candidate.word == entry.word or candidate.word in seen_words:
                return
            seen_words.add(candidate.word)
            selected.append(candidate)

        for candidate in priority_candidate_map.get(entry.word, []):
            add_candidate(candidate)
            if len(selected) >= candidate_limit:
                break

        candidate_words: set[str] = set()
        for key in build_listening_bucket_keys(entry):
            candidate_words.update(buckets[key])

        ranked = sorted(
            [
                entries_by_word[candidate_word]
                for candidate_word in candidate_words
                if candidate_word in entries_by_word
                and candidate_word != entry.word
                and _is_high_value_listening_candidate(entry, entries_by_word[candidate_word])
            ],
            key=lambda candidate: _high_value_listening_candidate_score(entry, candidate),
            reverse=True,
        )

        for candidate in ranked:
            add_candidate(candidate)
            if len(selected) >= candidate_limit:
                break

        if selected:
            presets[entry.word] = [
                serialize_word_entry(candidate)
                for candidate in selected[:candidate_limit]
            ]

    return presets
