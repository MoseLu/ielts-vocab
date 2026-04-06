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
HIGH_VALUE_PRESET_OUTPUT_PATH = VOCAB_DIR / "ielts_high_value_confusables.json"
PRIORITY_GROUPS_PATH = VOCAB_DIR / "confusable_priority_groups.json"

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
HIGH_VALUE_PRESET_TARGET_MIN_CANDIDATES = 2

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
