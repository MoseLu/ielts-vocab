#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate comprehensive chapter comparison report.
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
    card_pattern = r'alt="([^"]+)"[^>]*>[^<]*</h5>.*?<span class="text-nowrap">(\d+)词</span>'
    matches = re.findall(card_pattern, content, re.DOTALL)
    return {title: int(count) for title, count in matches}


def main():
    source_dir = r'C:/Users/12081/Desktop/词库'

    # Parse HTML (correct counts)
    html_chapters = parse_html_chapters(os.path.join(source_dir, '听力高频词.txt'))

    # Parse our JSON output
    with open('vocabulary_data/ielts_listening_premium.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    print("=" * 80)
    print("听力高频词 - 章节对比报告")
    print("=" * 80)

    # Build comparison table
    results = []
    html_total = 0
    parsed_total = 0
    diff_count = 0

    for ch in data['chapters']:
        title = ch['title']
        parsed = ch['word_count']
        html = html_chapters.get(title)

        parsed_total += parsed

        if html is not None:
            html_total += html
            diff = parsed - html
            if diff != 0:
                diff_count += 1
            results.append((title, html, parsed, diff))
        else:
            # Chapter not in HTML
            results.append((title, '缺失', parsed, 'N/A'))

    # Print summary
    print(f"\nHTML章节总数: {len(html_chapters)} (网站显示73章节)")
    print(f"解析章节总数: {len(data['chapters'])}")
    print(f"HTML词汇总和: {html_total}")
    print(f"解析词汇总和: {parsed_total}")
    print(f"目标词汇数: 3685")
    print(f"\n有差异的章节数: {diff_count}")

    # Print detailed comparison
    print("\n" + "-" * 80)
    print(f"{'章节名':<25} {'HTML正确':>10} {'解析结果':>10} {'差异':>8}")
    print("-" * 80)

    for title, html, parsed, diff in results:
        if html == '缺失':
            print(f"{title:<25} {html:>10} {parsed:>10} {'新增章节':>8}")
        elif diff != 0:
            print(f"{title:<25} {html:>10} {parsed:>10} {diff:>+8}")

    # Print chapters in HTML but not in JSON
    json_titles = {ch['title'] for ch in data['chapters']}
    missing_in_json = [t for t in html_chapters.keys() if t not in json_titles]
    if missing_in_json:
        print("\nHTML中有但解析缺失的章节:")
        for title in missing_in_json:
            print(f"  - {title} ({html_chapters[title]}词)")

    # Calculate expected total
    print("\n" + "=" * 80)
    print("结论分析")
    print("=" * 80)

    # Account for missing chapter
    missing_chapter_words = 50  # Estimated for 听力原文6次①
    expected_html_total = html_total + missing_chapter_words

    print(f"1. HTML解析词汇总和: {html_total} (缺一章约{missing_chapter_words}词)")
    print(f"2. 预估HTML完整词汇: {expected_html_total}")
    print(f"3. 解析JSON词汇总和: {parsed_total}")
    print(f"4. 差异 (2-3): {expected_html_total - parsed_total}")
    print(f"5. 目标词汇数: 3685")
    print(f"6. 超出词汇 (2-5): {expected_html_total - 3685}")
    print(f"\n结论: 原始数据比目标多{expected_html_total - 3685}词，可能存在跨章节重复词汇")


if __name__ == '__main__':
    main()