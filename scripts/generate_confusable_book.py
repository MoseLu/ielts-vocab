from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
VOCAB_DIR = ROOT / "vocabulary_data"
OUTPUT_PATH = VOCAB_DIR / "ielts_confusable_match.json"
LISTENING_PRESET_OUTPUT_PATH = VOCAB_DIR / "ielts_listening_confusables.json"

PHONETIC_SOURCE_FILES = [
    "ielts_reading_premium.json",
    "ielts_listening_premium.json",
]

LISTENING_PRESET_SOURCE_FILES = [
    "ielts_reading_premium.json",
    "ielts_listening_premium.json",
    "ielts_vocabulary_6260.csv",
    "ielts_vocabulary_ultimate.csv",
    "ielts_vocabulary_awl_extended.json",
    "ielts_9400_extended.json",
]

SPELLING_SOURCE_FILES = [
    "ielts_reading_premium.json",
    "ielts_listening_premium.json",
    "ielts_vocabulary_6260.csv",
    "ielts_9400_extended.json",
]

BOOK_ID = "ielts_confusable_match"
BOOK_TITLE = "雅思易混词辨析"
BOOK_DESCRIPTION = (
    "基于现有雅思词书自动抽取的音近词、形近词与词族近形辨析专用词书，"
    "支持多组消消乐匹配。"
)

PHONETIC_GROUPS_PER_CHAPTER = 60
SPELLING_GROUPS_PER_CHAPTER = 60
PHONETIC_GROUP_TARGET = 120
SPELLING_GROUP_TARGET = 420
MAX_WORDS_PER_SPELLING_GROUP = 5
LISTENING_PRESET_CANDIDATE_LIMIT = 6
LISTENING_PRESET_MIN_CANDIDATES = 3

BAD_DEFINITION_TOKENS = (
    "复数",
    "现在分词",
    "过去式",
    "过去分词",
    "比较级",
    "最高级",
    "人名",
)
WORD_RE = re.compile(r"^[a-z]{4,15}$")
LISTENING_WORD_RE = re.compile(r"^[a-z]{1,}(?:[-'][a-z]+)*(?: [a-z]{1,}(?:[-'][a-z]+)*)*$")

DISALLOWED_WORDS = {
    "loch",
    "quay",
}

DISALLOWED_PAIRS = {
    ("behavior", "behaviour"),
    ("judgement", "judgment"),
}

DEFAULT_FREQUENCY_BY_SOURCE = {
    "ielts_reading_premium.json": 78,
    "ielts_listening_premium.json": 78,
    "ielts_vocabulary_6260.csv": 72,
    "ielts_9400_extended.json": 60,
}


@dataclass(frozen=True)
class WordEntry:
    word: str
    phonetic: str
    pos: str
    definition: str
    source: str
    rank: int
    frequency: int
    normalized_phonetic: str
    normalized_definition: str
    stem: str


@dataclass(frozen=True)
class PairCandidate:
    left: WordEntry
    right: WordEntry
    score: float
    word_similarity: float
    phonetic_similarity: float
    prefix_length: int
    edit_distance: int


@dataclass(frozen=True)
class WordGroup:
    kind: str
    score: float
    words: list[WordEntry]


def serialize_word_entry(entry: WordEntry) -> dict[str, str]:
    return {
        "word": entry.word,
        "phonetic": entry.phonetic,
        "pos": entry.pos,
        "definition": entry.definition,
    }


def clean_word_text(raw_word: str) -> str:
    normalized = raw_word.strip().lower()
    normalized = normalized.replace("…", " ")
    normalized = re.sub(r"\.+", " ", normalized)
    normalized = re.sub(r"(?<=s)'(?=\s|$)", "", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    normalized = normalized.strip()
    normalized = re.sub(
        r"\s+(?:n|v|vi|vt|adj|adv|prep|conj|pron|det|num|phrase)\s*$",
        "",
        normalized,
    )
    return normalized.strip(" .")


def normalize_phonetic(text: str) -> str:
    normalized = text.lower().strip()
    replacements = {
        "/": "",
        "[": "",
        "]": "",
        "ˈ": "",
        "ˌ": "",
        ":": "",
        "ɜː": "ɜ",
        "ɔː": "ɔ",
        "ɑː": "ɑ",
        "iː": "i",
        "uː": "u",
        "əʊ": "oʊ",
    }
    for source, target in replacements.items():
        normalized = normalized.replace(source, target)
    return re.sub(r"\s+", "", normalized)


def pseudo_phonetic(word: str) -> str:
    normalized = word.lower().strip()
    normalized = normalized.replace("'", "").replace("-", "").replace(" ", "")
    replacements = [
        ("tion", "shn"),
        ("sion", "shn"),
        ("ture", "cher"),
        ("ough", "o"),
        ("augh", "af"),
        ("eigh", "a"),
        ("ph", "f"),
        ("ght", "t"),
        ("kn", "n"),
        ("wr", "r"),
        ("wh", "w"),
        ("qu", "kw"),
        ("ck", "k"),
        ("dge", "j"),
        ("tch", "ch"),
        ("ch", "x"),
        ("sh", "x"),
        ("th", "0"),
        ("dg", "j"),
        ("ge", "j"),
        ("gi", "j"),
        ("gy", "j"),
        ("ce", "s"),
        ("ci", "s"),
        ("cy", "s"),
        ("x", "ks"),
        ("q", "k"),
        ("v", "f"),
        ("z", "s"),
        ("oo", "u"),
        ("ee", "i"),
        ("ea", "i"),
        ("ie", "i"),
        ("ei", "i"),
        ("ai", "e"),
        ("ay", "e"),
        ("oa", "o"),
        ("ou", "u"),
        ("ow", "o"),
        ("au", "o"),
        ("aw", "o"),
    ]
    for source, target in replacements:
        normalized = normalized.replace(source, target)
    normalized = re.sub(r"([aeiouy])\1+", r"\1", normalized)
    normalized = re.sub(r"[aeiouy]+", "a", normalized)
    return normalized


def normalize_definition(text: str) -> str:
    normalized = text.strip().lower()
    normalized = re.sub(r"[；;，,、。.\-—/()\[\]“”\"'·<>]", "", normalized)
    normalized = re.sub(r"\s+", "", normalized)
    return normalized


def stem_word(word: str) -> str:
    for suffix in ("ing", "ed", "es", "s"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 4:
            return word[: -len(suffix)]
    if word.endswith("men") and len(word) > 5:
        return word[:-3] + "man"
    if word.endswith("ies") and len(word) > 5:
        return word[:-3] + "y"
    return word


def edit_distance(left: str, right: str) -> int:
    dp = list(range(len(right) + 1))
    for index, left_char in enumerate(left, start=1):
        previous = dp[0]
        dp[0] = index
        for j, right_char in enumerate(right, start=1):
            current = dp[j]
            dp[j] = min(
                dp[j] + 1,
                dp[j - 1] + 1,
                previous + (left_char != right_char),
            )
            previous = current
    return dp[-1]


def common_prefix_length(left: str, right: str) -> int:
    size = 0
    limit = min(len(left), len(right))
    while size < limit and left[size] == right[size]:
        size += 1
    return size


def word_similarity(left: str, right: str) -> float:
    return SequenceMatcher(None, left, right).ratio()


def definition_similarity(left: WordEntry, right: WordEntry) -> float:
    return SequenceMatcher(
        None,
        left.normalized_definition,
        right.normalized_definition,
    ).ratio()


def phonetic_similarity(left: WordEntry, right: WordEntry) -> float:
    if not left.normalized_phonetic or not right.normalized_phonetic:
        return 0.0
    return SequenceMatcher(
        None,
        left.normalized_phonetic,
        right.normalized_phonetic,
    ).ratio()


def should_skip_word(word: str, definition: str, phonetic: str, *, require_phonetic: bool) -> bool:
    if word in DISALLOWED_WORDS:
        return True
    if not WORD_RE.fullmatch(word):
        return True
    if not definition.strip():
        return True
    if require_phonetic and not phonetic.strip():
        return True
    return any(token in definition for token in BAD_DEFINITION_TOKENS)


def should_skip_listening_word(word: str, definition: str) -> bool:
    if not LISTENING_WORD_RE.fullmatch(word):
        return True
    if not definition.strip():
        return True
    return False


def parse_frequency(raw_word: dict, source_name: str) -> int:
    raw_value = raw_word.get("frequency")
    if raw_value in (None, ""):
        return DEFAULT_FREQUENCY_BY_SOURCE.get(source_name, 70)
    try:
        return int(raw_value)
    except (TypeError, ValueError):
        return DEFAULT_FREQUENCY_BY_SOURCE.get(source_name, 70)


def iter_source_words(source_name: str) -> Iterable[dict]:
    source_path = VOCAB_DIR / source_name

    if source_name.endswith(".csv"):
        with source_path.open("r", encoding="utf-8-sig", newline="") as file_obj:
            for row in csv.DictReader(file_obj):
                yield {
                    "word": row.get("word", ""),
                    "phonetic": row.get("phonetic", ""),
                    "pos": row.get("pos", "") or "n.",
                    "definition": row.get("definition", "") or row.get("translation", ""),
                    "frequency": row.get("frequency"),
                }
        return

    payload = json.loads(source_path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and "chapters" in payload:
        for chapter in payload.get("chapters", []):
            for word in chapter.get("words", []):
                yield word
        return

    if isinstance(payload, list):
        for word in payload:
            yield word


def load_entries(source_files: list[str], *, require_phonetic: bool) -> list[WordEntry]:
    deduped: dict[str, WordEntry] = {}
    rank = 0

    for source_name in source_files:
        for raw_word in iter_source_words(source_name):
            rank += 1
            word = clean_word_text(str(raw_word.get("word", "")))
            phonetic = str(raw_word.get("phonetic", "")).strip()
            pos = str(raw_word.get("pos", "")).strip() or "n."
            definition = str(
                raw_word.get("definition", "") or raw_word.get("translation", "")
            ).strip()
            if should_skip_word(word, definition, phonetic, require_phonetic=require_phonetic):
                continue

            candidate = WordEntry(
                word=word,
                phonetic=phonetic,
                pos=pos,
                definition=definition,
                source=source_name,
                rank=rank,
                frequency=parse_frequency(raw_word, source_name),
                normalized_phonetic=normalize_phonetic(phonetic),
                normalized_definition=normalize_definition(definition),
                stem=stem_word(word),
            )
            current = deduped.get(word)
            if current is None or candidate.rank < current.rank:
                deduped[word] = candidate

    return list(deduped.values())


def load_listening_entries(source_files: list[str]) -> list[WordEntry]:
    deduped: dict[str, WordEntry] = {}
    rank = 0

    for source_name in source_files:
        for raw_word in iter_source_words(source_name):
            rank += 1
            word = clean_word_text(str(raw_word.get("word", "")))
            phonetic = str(raw_word.get("phonetic", "")).strip()
            pos = str(raw_word.get("pos", "")).strip() or "n."
            definition = str(
                raw_word.get("definition", "") or raw_word.get("translation", "")
            ).strip()
            if should_skip_listening_word(word, definition):
                continue

            normalized_phonetic = normalize_phonetic(phonetic) if phonetic else pseudo_phonetic(word)
            candidate = WordEntry(
                word=word,
                phonetic=phonetic,
                pos=pos,
                definition=definition,
                source=source_name,
                rank=rank,
                frequency=parse_frequency(raw_word, source_name),
                normalized_phonetic=normalized_phonetic,
                normalized_definition=normalize_definition(definition),
                stem=stem_word(word),
            )
            current = deduped.get(word)
            if current is None:
                deduped[word] = candidate
                continue

            current_priority = (1 if current.phonetic else 0, -current.rank)
            candidate_priority = (1 if candidate.phonetic else 0, -candidate.rank)
            if candidate_priority > current_priority:
                deduped[word] = candidate

    return list(deduped.values())


def are_same_lexeme(left: WordEntry, right: WordEntry) -> bool:
    pair_key = tuple(sorted((left.word, right.word)))
    if pair_key in DISALLOWED_PAIRS:
        return True
    if left.stem == right.stem and word_similarity(left.word, right.word) >= 0.84:
        return True
    if left.normalized_definition == right.normalized_definition:
        return True
    if definition_similarity(left, right) >= 0.95 and word_similarity(left.word, right.word) >= 0.8:
        return True
    return False


def build_phonetic_keys(entry: WordEntry) -> set[tuple[int, str, str]]:
    phonetic = entry.normalized_phonetic
    return {
        (len(phonetic), phonetic[:2], phonetic[-2:]),
        (len(phonetic), phonetic[:3], phonetic[-1:]),
        (len(phonetic) - 1, phonetic[:2], phonetic[-2:]),
        (len(phonetic) + 1, phonetic[:2], phonetic[-2:]),
        (len(phonetic) - 2, phonetic[:2], phonetic[-2:]),
        (len(phonetic) + 2, phonetic[:2], phonetic[-2:]),
    }


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


def main() -> None:
    phonetic_entries = load_entries(PHONETIC_SOURCE_FILES, require_phonetic=True)
    spelling_entries = load_entries(SPELLING_SOURCE_FILES, require_phonetic=False)
    listening_preset_entries = load_listening_entries(LISTENING_PRESET_SOURCE_FILES)

    phonetic_candidates = build_phonetic_candidates(phonetic_entries)
    phonetic_groups = select_phonetic_groups(
        phonetic_candidates,
        target_groups=PHONETIC_GROUP_TARGET,
    )
    spelling_groups = select_spelling_groups(
        build_spelling_candidates(spelling_entries),
        target_groups=SPELLING_GROUP_TARGET,
    )
    listening_presets = build_listening_presets(
        listening_preset_entries,
        candidate_limit=LISTENING_PRESET_CANDIDATE_LIMIT,
        minimum_candidates=LISTENING_PRESET_MIN_CANDIDATES,
    )
    listening_candidate_lengths = [len(candidates) for candidates in listening_presets.values()]

    chapters: list[dict] = []
    next_chapter_id = 1

    phonetic_chapters, next_chapter_id = build_chapters(
        chapter_title="音近词辨析",
        groups=phonetic_groups,
        groups_per_chapter=PHONETIC_GROUPS_PER_CHAPTER,
        starting_id=next_chapter_id,
    )
    chapters.extend(phonetic_chapters)

    spelling_chapters, next_chapter_id = build_chapters(
        chapter_title="形近词辨析",
        groups=spelling_groups,
        groups_per_chapter=SPELLING_GROUPS_PER_CHAPTER,
        starting_id=next_chapter_id,
    )
    chapters.extend(spelling_chapters)

    payload = {
        "book_id": BOOK_ID,
        "title": BOOK_TITLE,
        "description": BOOK_DESCRIPTION,
        "total_chapters": len(chapters),
        "total_words": sum(chapter["word_count"] for chapter in chapters),
        "chapters": chapters,
    }

    OUTPUT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    LISTENING_PRESET_OUTPUT_PATH.write_text(
        json.dumps({
            "candidate_limit": LISTENING_PRESET_CANDIDATE_LIMIT,
            "minimum_candidates": LISTENING_PRESET_MIN_CANDIDATES,
            "sources": LISTENING_PRESET_SOURCE_FILES,
            "total_words": len(listening_presets),
            "min_candidates_per_word": min(listening_candidate_lengths) if listening_candidate_lengths else 0,
            "max_candidates_per_word": max(listening_candidate_lengths) if listening_candidate_lengths else 0,
            "words": listening_presets,
        }, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"Wrote {OUTPUT_PATH}")
    print(f"Wrote {LISTENING_PRESET_OUTPUT_PATH}")
    print(
        f"Phonetic groups: {len(phonetic_groups)} | Spelling groups: {len(spelling_groups)} "
        f"| Chapters: {len(chapters)} | Words: {payload['total_words']}"
    )
    print(
        f"Listening presets: {len(listening_presets)} words "
        f"| min candidates: {min(listening_candidate_lengths) if listening_candidate_lengths else 0} "
        f"| max candidates: {max(listening_candidate_lengths) if listening_candidate_lengths else 0}"
    )
    for chapter in chapters[:4]:
        print(
            f"  {chapter['title']}: {chapter['word_count']} words "
            f"({len({word['group_key'] for word in chapter['words']})} groups)"
        )


if __name__ == "__main__":
    main()
