#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analyze chapter-by-chapter word counts in original vocabulary files.
"""
import re
import os
import sys

# Fix encoding for Windows console
sys.stdout.reconfigure(encoding='utf-8')

def analyze_txt_file(file_path):
    """Analyze a TXT vocabulary file with chapter structure."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Try different chapter patterns
    # Pattern 1: 【数字】标题
    chapter_pattern = r'【(\d+)】([^\n]+)\n'
    parts = re.split(chapter_pattern, content)

    if len(parts) <= 3:
        # Pattern 2: 数字. 标题
        chapter_pattern = r'(\d+)\.\s+([^\n]+)\n'
        parts = re.split(chapter_pattern, content)

    if len(parts) <= 3:
        # Pattern 3: Look for word entries and group by any separator
        # Just count all words with phonetic
        words = re.findall(r'([a-zA-Z][a-zA-Z\s\-\x27.]*?)\s*/[^/]+/', content)
        return [], len(words)

    chapter_stats = []
    total_words = 0

    # parts[0] is content before first chapter
    # Then: id, title, content, id, title, content...
    i = 1
    while i < len(parts) - 2:
        try:
            ch_id = int(parts[i])
        except ValueError:
            i += 1
            continue
        ch_title = parts[i+1].strip()
        ch_content = parts[i+2]

        # Count words with phonetic pattern
        words = re.findall(r'([a-zA-Z][a-zA-Z\s\-\x27.]*?)\s*/[^/]+/', ch_content)
        word_count = len(words)

        chapter_stats.append({
            'id': ch_id,
            'title': ch_title,
            'word_count': word_count
        })
        total_words += word_count
        i += 3

    return chapter_stats, total_words


def analyze_json_file(file_path, first_group_excel=None):
    """Analyze a JSON vocabulary file with chapter structure."""
    import json

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    chapter_stats = []
    total_words = 0

    for idx, group in enumerate(data):
        label = group.get('label', '')
        word_text = group.get('wordText', '')

        if not word_text or word_text.startswith('数据加载中'):
            continue

        # Count words with phonetic pattern
        words = re.findall(r'([a-zA-Z][a-zA-Z\s\-\x27.]*?)\s*/[^/]+/', word_text)
        word_count = len(words)

        chapter_stats.append({
            'id': idx + 1,
            'title': label,
            'word_count': word_count
        })
        total_words += word_count

    return chapter_stats, total_words


def main():
    source_dir = r'C:/Users/12081/Desktop/词库'
    output_file = 'vocabulary_data/_chapter_analysis.txt'

    results = []

    results.append("=" * 60)
    results.append("听力高频词 JSON 文件章节分析")
    results.append("=" * 60)

    json_file = os.path.join(source_dir, '听力高频词_2026-03-17.json')
    if os.path.exists(json_file):
        chapters, total = analyze_json_file(json_file)
        results.append(f"\n总章节数: {len(chapters)}")
        results.append(f"总词汇数: {total}")
        results.append(f"目标词汇数: 3685")
        results.append(f"差异: {total - 3685} 词")
        results.append("\n章节详情:")
        for ch in chapters:
            results.append(f"  章节{ch['id']:2d}: {ch['title'][:25]:25s} - {ch['word_count']:3d} 词")

    # Write to file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(results))

    print(f"分析结果已保存到: {output_file}")
    print(f"JSON总词汇数: {total}, 目标: 3685, 差异: {total - 3685}")


if __name__ == '__main__':
    main()