def build_spelling_keys(entry: WordEntry) -> set[tuple[int, str, int]]:
    keys: set[tuple[int, str, int]] = set()
    for prefix_size in (3, 4):
        prefix = entry.word[:prefix_size]
        for length in range(len(entry.word) - 3, len(entry.word) + 4):
            keys.add((prefix_size, prefix, length))
    return keys


def build_listening_bucket_keys(entry: WordEntry) -> set[tuple]:
    word = entry.word
    phonetic = entry.normalized_phonetic
    tokens = word.split(" ")
    keys: set[tuple] = {
        ("p2", len(phonetic), phonetic[:2], phonetic[-2:]),
        ("p3", len(phonetic), phonetic[:3], phonetic[-1:]),
        ("pb", max(1, len(phonetic) // 2), phonetic[:2]),
        ("s2", len(word), word[:2], word[-2:]),
        ("s3", len(word), word[:3], word[-1:]),
        ("sb", max(1, len(word) // 2), word[:3]),
        ("first", tokens[0][:3], len(tokens)),
        ("last", tokens[-1][:3], len(tokens)),
    }

    if len(tokens) == 1:
        keys.add(("mid", word[1:4] if len(word) >= 4 else word, len(word)))
        if len(word) <= 3:
            keys.add(("short", len(word), word[:1]))
            keys.add(("shortp", len(phonetic), phonetic[:1]))
    else:
        keys.add(("phrase", len(tokens[0]), len(tokens[-1]), len(tokens)))

    return keys


def build_phonetic_candidates(entries: list[WordEntry]) -> list[PairCandidate]:
    buckets: defaultdict[tuple[int, str, str], list[WordEntry]] = defaultdict(list)
    for entry in entries:
        for key in build_phonetic_keys(entry):
            buckets[key].append(entry)

    seen_pairs: set[tuple[str, str]] = set()
    candidates: list[PairCandidate] = []

    for bucket in buckets.values():
        if len(bucket) < 2:
            continue

        for index, left in enumerate(bucket):
            for right in bucket[index + 1 :]:
                pair_key = tuple(sorted((left.word, right.word)))
                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)

                if are_same_lexeme(left, right):
                    continue

                word_ratio = word_similarity(left.word, right.word)
                phonetic_ratio = phonetic_similarity(left, right)
                if phonetic_ratio < 0.82:
                    continue
                if abs(len(left.word) - len(right.word)) > 3:
                    continue
                if word_ratio > 0.97:
                    continue

                frequency_bonus = (left.frequency + right.frequency - 120) / 8
                rank_bonus = max(0.0, 14000 - (left.rank + right.rank)) / 14000 * 18
                score = (
                    phonetic_ratio * 100
                    + word_ratio * 16
                    + frequency_bonus
                    + rank_bonus
                    - abs(len(left.word) - len(right.word)) * 5
                )

                candidates.append(
                    PairCandidate(
                        left=left,
                        right=right,
                        score=score,
                        word_similarity=word_ratio,
                        phonetic_similarity=phonetic_ratio,
                        prefix_length=common_prefix_length(left.word, right.word),
                        edit_distance=edit_distance(left.word, right.word),
                    )
                )

    candidates.sort(key=lambda candidate: candidate.score, reverse=True)
    return candidates


def build_spelling_candidates(entries: list[WordEntry]) -> list[PairCandidate]:
    buckets: defaultdict[tuple[int, str, int], list[WordEntry]] = defaultdict(list)
    for entry in entries:
        for key in build_spelling_keys(entry):
            buckets[key].append(entry)

    seen_pairs: set[tuple[str, str]] = set()
    candidates: list[PairCandidate] = []

    for bucket in buckets.values():
        if len(bucket) < 2:
            continue

        for index, left in enumerate(bucket):
            for right in bucket[index + 1 :]:
                pair_key = tuple(sorted((left.word, right.word)))
                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)

                if are_same_lexeme(left, right):
                    continue

                prefix_length = common_prefix_length(left.word, right.word)
                word_ratio = word_similarity(left.word, right.word)
                distance = edit_distance(left.word, right.word)
                length_delta = abs(len(left.word) - len(right.word))

                if prefix_length < 3 or length_delta > 3:
                    continue
                if distance > 4 and word_ratio < 0.68:
                    continue

                frequency_bonus = (left.frequency + right.frequency - 120) / 8
                rank_bonus = max(0.0, 16000 - (left.rank + right.rank)) / 16000 * 18
                phonetic_penalty = max(0.0, phonetic_similarity(left, right) - 0.92) * 8
                score = (
                    prefix_length * 9
                    + word_ratio * 70
                    - distance * 7
                    - length_delta * 4
                    + frequency_bonus
                    + rank_bonus
                    - phonetic_penalty
                )

                candidates.append(
                    PairCandidate(
                        left=left,
                        right=right,
                        score=score,
                        word_similarity=word_ratio,
                        phonetic_similarity=phonetic_similarity(left, right),
                        prefix_length=prefix_length,
                        edit_distance=distance,
                    )
                )

    candidates.sort(key=lambda candidate: candidate.score, reverse=True)
    return candidates


def select_phonetic_groups(candidates: list[PairCandidate], target_groups: int) -> list[WordGroup]:
    selected: list[WordGroup] = []
    usage = Counter()

    for candidate in candidates:
        if usage[candidate.left.word] >= 2 or usage[candidate.right.word] >= 2:
            continue
        selected.append(
            WordGroup(
                kind="phonetic",
                score=candidate.score,
                words=[candidate.left, candidate.right],
            )
        )
        usage[candidate.left.word] += 1
        usage[candidate.right.word] += 1
        if len(selected) >= target_groups:
            break

    if len(selected) < target_groups:
        raise RuntimeError(
            f"Only selected {len(selected)} phonetic groups, expected at least {target_groups}."
        )

    return selected


def spelling_family_key(candidate: PairCandidate) -> str:
    prefix_size = 4 if candidate.prefix_length >= 4 else 3
    return candidate.left.word[:prefix_size]


def select_spelling_groups(candidates: list[PairCandidate], target_groups: int) -> list[WordGroup]:
    families: defaultdict[str, list[PairCandidate]] = defaultdict(list)
    for candidate in candidates:
        families[spelling_family_key(candidate)].append(candidate)

    groups: list[WordGroup] = []

    for family_key, family_candidates in families.items():
        family_candidates.sort(key=lambda candidate: candidate.score, reverse=True)
        entries_by_word: dict[str, WordEntry] = {}
        adjacency: defaultdict[str, list[PairCandidate]] = defaultdict(list)

        for candidate in family_candidates:
            entries_by_word[candidate.left.word] = candidate.left
            entries_by_word[candidate.right.word] = candidate.right
            adjacency[candidate.left.word].append(candidate)
            adjacency[candidate.right.word].append(candidate)

        usage = Counter()
        anchor_scores: list[tuple[float, str]] = []
        for word, word_candidates in adjacency.items():
            best_scores = [candidate.score for candidate in word_candidates[:3]]
            anchor_entry = entries_by_word[word]
            best_average = sum(best_scores) / max(len(best_scores), 1)
            anchor_metric = (
                best_average
                + min(len(word_candidates), 6) * 5
                + anchor_entry.frequency * 0.8
                - len(word) * 3
                - anchor_entry.rank / 8000
            )
            anchor_scores.append((anchor_metric, word))

        max_groups_in_family = 2 if len(entries_by_word) >= 8 else 1
        for _, anchor_word in sorted(anchor_scores, reverse=True):
            if max_groups_in_family <= 0:
                break
            if usage[anchor_word] >= 2:
                continue

            anchor_entry = entries_by_word[anchor_word]
            group_words = [anchor_entry]
            seen_words = {anchor_word}
            group_edge_scores: list[float] = []

            for candidate in adjacency[anchor_word]:
                neighbor = candidate.right if candidate.left.word == anchor_word else candidate.left
                if neighbor.word in seen_words:
                    continue
                if usage[neighbor.word] >= 2:
                    continue
                group_words.append(neighbor)
                seen_words.add(neighbor.word)
                group_edge_scores.append(candidate.score)
                if len(group_words) >= MAX_WORDS_PER_SPELLING_GROUP:
                    break

            if len(group_words) < 3:
                continue

            groups.append(
                WordGroup(
                    kind="spelling",
                    score=(
                        sum(group_edge_scores) / len(group_edge_scores)
                        + anchor_entry.frequency * 0.4
                        - len(anchor_word) * 2
                    ),
                    words=group_words,
                )
            )
            for word in group_words:
                usage[word.word] += 1
            max_groups_in_family -= 1

    groups.sort(key=lambda group: group.score, reverse=True)

    if len(groups) < target_groups:
        raise RuntimeError(
            f"Only selected {len(groups)} spelling groups, expected at least {target_groups}."
        )

    return groups[:target_groups]


def common_suffix_length(left: str, right: str) -> int:
    size = 0
    limit = min(len(left), len(right))
    while size < limit and left[-(size + 1)] == right[-(size + 1)]:
        size += 1
    return size


def listening_confusability_score(target: WordEntry, candidate: WordEntry) -> float:
    word_ratio = word_similarity(target.word, candidate.word)
    phonetic_ratio = phonetic_similarity(target, candidate)
    prefix_length = common_prefix_length(target.word, candidate.word)
    suffix_length = common_suffix_length(target.word, candidate.word)
    score = (
        phonetic_ratio * 70
        + word_ratio * 25
        + prefix_length * 3
        + suffix_length * 1.5
        - abs(len(target.word) - len(candidate.word)) * 2
    )

    if target.pos == candidate.pos:
        score += 4

    target_tokens = target.word.split(" ")
    candidate_tokens = candidate.word.split(" ")
    if len(target_tokens) == len(candidate_tokens):
        score += 3
    if target_tokens and candidate_tokens and target_tokens[0] == candidate_tokens[0]:
        score += 10
    if target_tokens and candidate_tokens and target_tokens[-1] == candidate_tokens[-1]:
        score += 18

    score += min(target.frequency, candidate.frequency) * 0.15
    score += max(0.0, 20000 - (target.rank + candidate.rank)) / 20000 * 12
    return score


def build_listening_candidate_buckets(entries: list[WordEntry]) -> defaultdict[tuple, set[str]]:
    buckets: defaultdict[tuple, set[str]] = defaultdict(set)
    for entry in entries:
        for key in build_listening_bucket_keys(entry):
            buckets[key].add(entry.word)
    return buckets


def rank_listening_candidates(
    target: WordEntry,
    entries_by_word: dict[str, WordEntry],
    candidate_words: set[str],
) -> list[WordEntry]:
    scored: list[tuple[float, WordEntry]] = []
    for candidate_word in candidate_words:
        if candidate_word == target.word:
            continue
        candidate = entries_by_word[candidate_word]
        if are_same_lexeme(target, candidate):
            continue
        scored.append((listening_confusability_score(target, candidate), candidate))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [candidate for _, candidate in scored]


def build_global_listening_fallback(
    target: WordEntry,
    entries: list[WordEntry],
    excluded_words: set[str],
) -> list[WordEntry]:
    scored: list[tuple[float, WordEntry]] = []
    for candidate in entries:
        if candidate.word == target.word or candidate.word in excluded_words:
            continue
        if are_same_lexeme(target, candidate):
            continue
        scored.append((listening_confusability_score(target, candidate), candidate))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [candidate for _, candidate in scored]


def build_listening_presets(
    entries: list[WordEntry],
    candidate_limit: int,
    minimum_candidates: int,
) -> dict[str, list[dict[str, str]]]:
    entries_by_word = {entry.word: entry for entry in entries}
    buckets = build_listening_candidate_buckets(entries)
    presets: dict[str, list[dict[str, str]]] = {}
    words_missing_fallback: list[str] = []

    for entry in entries:
        candidate_words: set[str] = set()
        for key in build_listening_bucket_keys(entry):
            candidate_words.update(buckets[key])
        ranked = rank_listening_candidates(entry, entries_by_word, candidate_words)
        selected = ranked[:candidate_limit]
        presets[entry.word] = [serialize_word_entry(candidate) for candidate in selected]

        if len(selected) < minimum_candidates:
            words_missing_fallback.append(entry.word)

    for word in words_missing_fallback:
        entry = entries_by_word[word]
        existing_words = {candidate["word"] for candidate in presets.get(word, [])}
        fallback_candidates = build_global_listening_fallback(entry, entries, existing_words)
        combined: list[dict[str, str]] = list(presets.get(word, []))
        seen_words = set(existing_words)

        for candidate in fallback_candidates:
            if candidate.word in seen_words:
                continue
            combined.append(serialize_word_entry(candidate))
            seen_words.add(candidate.word)
            if len(combined) >= candidate_limit:
                break

        presets[word] = combined

    return presets


def build_chapters(
    chapter_title: str,
    groups: list[WordGroup],
    groups_per_chapter: int,
    starting_id: int,
) -> tuple[list[dict], int]:
    chapters: list[dict] = []
    chapter_id = starting_id

    for offset in range(0, len(groups), groups_per_chapter):
        chunk = groups[offset : offset + groups_per_chapter]
        words: list[dict[str, str]] = []

        for group_index, group in enumerate(chunk, start=1):
            group_key = f"{group.kind}-{chapter_id}-{group_index:03d}"
            for entry in group.words:
                words.append(
                    {
                        "word": entry.word,
                        "phonetic": entry.phonetic,
                        "pos": entry.pos,
                        "definition": entry.definition,
                        "group_key": group_key,
                    }
                )

        chapters.append(
            {
                "id": chapter_id,
                "title": f"{chapter_title} {chapter_id - starting_id + 1:02d}",
                "word_count": len(words),
                "words": words,
            }
        )
        chapter_id += 1

    return chapters, chapter_id
