#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Find duplicate words across chapters in the JSON vocabulary file.
"""
import re
import json
import os
import sys
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')


def extract_all_words(file_path):
    """Extract all words with their chapter info from JSON file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    word_chapters = defaultdict(list)  # word -> list of (chapter_id, chapter_title)

    for idx, group in enumerate(data):
        label = group.get('label', '')
        word_text = group.get('wordText', '')

        if not word_text or word_text.startswith('数据加载中'):
            continue

        chapter_id = idx + 1

        # Find all words with phonetic pattern (handle both /phonetic/ and //phonetic//)
        words = re.findall(r'([a-zA-Z][a-zA-Z\s\-\x27.]*?)\s*(?://|/)[^/]+(?://|/)', word_text)

        for word in words:
            word_lower = word.lower().strip()
            if len(word_lower) >= 2:
                word_chapters[word_lower].append((chapter_id, label))

    return word_chapters


def main():
    json_file = r'C:/Users/12081/Desktop/词库/听力高频词_2026-03-17.json'
    word_chapters = extract_all_words(json_file)

    total_entries = sum(len(v) for v in word_chapters.values())
    unique_words = len(word_chapters)

    print(f"总词条数: {total_entries}")
    print(f"唯一词汇数: {unique_words}")
    print(f"重复词条数: {total_entries - unique_words}")

    # Find duplicates
    duplicates = {w: chapters for w, chapters in word_chapters.items() if len(chapters) > 1}

    print(f"\n重复词汇数: {len(duplicates)}")

    # Count duplicates per chapter
    chapter_dup_count = defaultdict(int)
    for word, chapters in duplicates.items():
        for ch_id, ch_title in chapters[1:]:  # Skip first occurrence
            chapter_dup_count[(ch_id, ch_title)] += 1

    print("\n各章节重复词数统计:")
    sorted_chapters = sorted(chapter_dup_count.items(), key=lambda x: x[1], reverse=True)
    for (ch_id, ch_title), count in sorted_chapters[:20]:
        print(f"  章节{ch_id:2d} ({ch_title[:20]:20s}): {count:3d} 个重复词")

    # Calculate: if we remove duplicates, how many words left?
    words_after_dedup = total_entries - sum(len(v) - 1 for v in word_chapters.values())
    print(f"\n去重后词汇数: {words_after_dedup}")
    print(f"目标词汇数: 3685")
    print(f"差异: {words_after_dedup - 3685}")

    # Save duplicate list
    output_file = 'vocabulary_data/_duplicate_words.txt'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"重复词汇列表 (共{len(duplicates)}个)\n")
        f.write("=" * 60 + "\n\n")
        for word, chapters in sorted(duplicates.items(), key=lambda x: len(x[1]), reverse=True):
            f.write(f"{word}: 出现{len(chapters)}次\n")
            for ch_id, ch_title in chapters:
                f.write(f"  - 章节{ch_id}: {ch_title}\n")
            f.write("\n")

    print(f"\n重复词汇详情已保存到: {output_file}")


if __name__ == '__main__':
    main()