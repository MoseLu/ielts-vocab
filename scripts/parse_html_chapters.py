#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extract chapter info from HTML file.
"""
import re
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

def parse_html_chapters(file_path):
    """Parse chapter info from HTML file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Extract total chapters and words
    total_match = re.search(r'(\d+)\s*章节\s*&\s*(\d+)\s*词', content)
    if total_match:
        total_chapters = int(total_match.group(1))
        total_words = int(total_match.group(2))
        print(f"从HTML提取: {total_chapters} 章节, {total_words} 词")
    else:
        print("未找到总统计")
        total_chapters = 0
        total_words = 0

    # Extract chapter cards
    # Pattern: alt="章节名">章节名</h5>...<span class="text-nowrap">XX词</span>
    # Or: truncate" alt="章节名">章节名...<span class="text-nowrap">XX词</span>

    chapters = []

    # Find all chapter card patterns
    # The pattern has: alt="title">title...<span class="text-nowrap">XX词</span>
    card_pattern = r'alt="([^"]+)"[^>]*>[^<]*</h5>.*?<span class="text-nowrap">(\d+)词</span>'
    matches = re.findall(card_pattern, content, re.DOTALL)

    for i, (title, word_count) in enumerate(matches):
        chapters.append({
            'id': i + 1,
            'title': title,
            'word_count': int(word_count)
        })

    return chapters, total_chapters, total_words


def main():
    source_dir = r'C:/Users/12081/Desktop/词库'

    # Parse HTML file
    html_file = os.path.join(source_dir, '听力高频词.txt')
    chapters, total_chapters, total_words = parse_html_chapters(html_file)

    print(f"\n找到 {len(chapters)} 个章节卡片")

    # Calculate sum from chapters
    sum_words = sum(ch['word_count'] for ch in chapters)
    print(f"章节词汇总和: {sum_words}")

    print("\n章节详情:")
    for ch in chapters:
        print(f"  章节{ch['id']:2d}: {ch['title']:25s} - {ch['word_count']:3d} 词")

    # Save to file
    output_file = 'vocabulary_data/_html_chapter_info.txt'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"HTML章节统计\n")
        f.write(f"总章节数: {total_chapters}\n")
        f.write(f"总词汇数: {total_words}\n")
        f.write(f"章节词汇总和: {sum_words}\n\n")
        for ch in chapters:
            f.write(f"章节{ch['id']:2d}: {ch['title']:25s} - {ch['word_count']:3d} 词\n")

    print(f"\n已保存到: {output_file}")


if __name__ == '__main__':
    main()