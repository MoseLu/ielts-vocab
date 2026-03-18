#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Compare JSON chapter counts with HTML (correct) counts.
"""
import re
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')


def parse_html_chapters(file_path):
    """Parse chapter info from HTML file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    chapters = []
    card_pattern = r'alt="([^"]+)"[^>]*>[^<]*</h5>.*?<span class="text-nowrap">(\d+)词</span>'
    matches = re.findall(card_pattern, content, re.DOTALL)

    for i, (title, word_count) in enumerate(matches):
        chapters.append({
            'id': i + 1,
            'title': title,
            'word_count': int(word_count)
        })

    return chapters


def parse_json_chapters(file_path):
    """Parse chapter info from JSON file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    chapters = []
    for idx, group in enumerate(data):
        label = group.get('label', '')
        word_text = group.get('wordText', '')

        if not word_text or word_text.startswith('数据加载中'):
            continue

        words = re.findall(r'([a-zA-Z][a-zA-Z\s\-\x27.]*?)\s*/[^/]+/', word_text)
        word_count = len(words)

        chapters.append({
            'id': idx + 1,
            'title': label,
            'word_count': word_count
        })

    return chapters


def main():
    source_dir = r'C:/Users/12081/Desktop/词库'

    # Parse both files
    html_chapters = parse_html_chapters(os.path.join(source_dir, '听力高频词.txt'))
    json_chapters = parse_json_chapters(os.path.join(source_dir, '听力高频词_2026-03-17.json'))

    print("=" * 80)
    print("章节对比分析 (HTML正确 vs JSON原始)")
    print("=" * 80)

    # Create title to count mapping
    html_map = {ch['title']: ch for ch in html_chapters}
    json_map = {ch['title']: ch for ch in json_chapters}

    # Find differences
    total_diff = 0
    missing_in_html = []
    missing_in_json = []

    print(f"\n{'章节':<25} {'HTML正确':>10} {'JSON原始':>10} {'差异':>8}")
    print("-" * 80)

    # Check all JSON chapters
    for ch in json_chapters:
        title = ch['title']
        json_count = ch['word_count']

        if title in html_map:
            html_count = html_map[title]['word_count']
            diff = json_count - html_count
            if diff != 0:
                print(f"{title:<25} {html_count:>10} {json_count:>10} {diff:>+8}")
                total_diff += diff
        else:
            missing_in_html.append(ch)
            print(f"{title:<25} {'--':>10} {json_count:>10} {'缺失':>8}")
            total_diff += json_count

    # Check for chapters in HTML but not in JSON
    for ch in html_chapters:
        if ch['title'] not in json_map:
            missing_in_json.append(ch)
            print(f"{ch['title']:<25} {ch['word_count']:>10} {'--':>10} {'新增':>8}")
            total_diff -= ch['word_count']

    print("-" * 80)
    print(f"总差异: {total_diff:+d} 词")

    html_sum = sum(ch['word_count'] for ch in html_chapters)
    json_sum = sum(ch['word_count'] for ch in json_chapters)

    print(f"\nHTML章节总和: {html_sum} 词 (共{len(html_chapters)}章)")
    print(f"JSON章节总和: {json_sum} 词 (共{len(json_chapters)}章)")
    print(f"目标词汇数: 3685 词")
    print(f"\n差异分析: JSON({json_sum}) - HTML({html_sum}) = {json_sum - html_sum}")
    print(f"HTML({html_sum}) - 目标(3685) = {html_sum - 3685}")

    if missing_in_html:
        print(f"\nJSON中有但HTML中缺失的章节:")
        for ch in missing_in_html:
            print(f"  - {ch['title']} ({ch['word_count']}词)")

    if missing_in_json:
        print(f"\nHTML中有但JSON中缺失的章节:")
        for ch in missing_in_json:
            print(f"  - {ch['title']} ({ch['word_count']}词)")


if __name__ == '__main__':
    main()