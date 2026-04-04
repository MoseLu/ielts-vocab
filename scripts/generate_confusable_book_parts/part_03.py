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
