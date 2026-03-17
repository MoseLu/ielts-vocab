#!/usr/bin/env python3
"""
Parse vocabulary files with chapter/group structure preserved.
"""
import json
import re
import os

def parse_word_entry(text):
    """Parse a single word entry like 'car /kɑː(r)/\nn. 小汽车\n熟'"""
    lines = text.strip().split('\n')
    if not lines:
        return None

    result = {
        'word': '',
        'phonetic': '',
        'pos': 'n.',
        'definition': ''
    }

    first_line = lines[0].strip()

    # Pattern: word /phonetic/ or word //phonetic// (with possible trailing content)
    # Handle both single and double slash phonetic notation
    match = re.match(r'^([a-zA-Z][a-zA-Z\s\-\'\.]*?)\s*(?://([^/]+)//|/([^/]+)/)(.*)$', first_line)
    if match:
        result['word'] = match.group(1).strip()
        # Handle both double slash and single slash phonetic
        phonetic = match.group(2) if match.group(2) else match.group(3)
        result['phonetic'] = '/' + phonetic + '/'
        trailing = match.group(4).strip()

        # Check if trailing has pos.definition pattern
        if trailing:
            pos_match = re.match(r'^([a-z]+\.)\s*(.*)', trailing)
            if pos_match:
                result['pos'] = pos_match.group(1)
                def_text = pos_match.group(2)
                # Stop at Chinese characters followed by English (likely word root)
                def_match = re.match(r'^([一-龥；，。、！？a-zA-Z\s\-]+?)(?=[a-zA-Z]{3,}[一-龥]|词根|例句|$)', def_text)
                if def_match:
                    result['definition'] = def_match.group(1).strip()
                else:
                    result['definition'] = def_text[:50] if len(def_text) > 50 else def_text
    else:
        # Try: word pos. definition (without phonetic)
        match = re.match(r'^([a-zA-Z][a-zA-Z\s\-\'\.]*?)\s+([a-z]+\.)\s*(.*)', first_line)
        if match:
            result['word'] = match.group(1).strip()
            result['pos'] = match.group(2)
            result['definition'] = match.group(3).strip()

    # Process remaining lines for definition if not found
    if not result['definition']:
        definitions = []
        for line in lines[1:]:
            line = line.strip()
            if line == '熟' or line.startswith('例句') or line.startswith('词根') or line.startswith('数据'):
                continue
            if line.startswith('n.') or line.startswith('v.') or line.startswith('adj.') or \
               line.startswith('adv.') or line.startswith('prep.') or line.startswith('conj.'):
                if result['pos'] == 'n.':
                    pos_match = re.match(r'^([a-z]+\.)\s*(.*)', line)
                    if pos_match:
                        result['pos'] = pos_match.group(1)
                        if pos_match.group(2):
                            definitions.append(pos_match.group(2))
                else:
                    definitions.append(line)
            elif line and not line.startswith('→') and not re.match(r'^[一-龥]{2,}[a-zA-Z]', line):
                definitions.append(line)

        if definitions:
            def_text = '；'.join([d.rstrip('；;') for d in definitions[:3] if d])
            result['definition'] = re.sub(r'[""\""].*[""\"\"]', '', def_text).strip()

    # Clean up definition
    result['definition'] = re.sub(r'[；;]\s*$', '', result['definition'])
    result['definition'] = re.sub(r'\s+', ' ', result['definition'])

    # Skip entries with empty word or definition
    if not result['word'] or not result['definition']:
        return None

    # Skip entries with malformed word
    if re.search(r'[一-龥]', result['word']) or len(result['word']) > 25:
        return None

    # Clean up word
    result['word'] = re.sub(r'\s+', ' ', result['word']).strip()

    return result


def parse_first_group_excel(file_path):
    """Parse the first group Excel file with columns: 单词, 音标, 释义"""
    import pandas as pd

    df = pd.read_excel(file_path)
    words = []

    for _, row in df.iterrows():
        word = row.get('单词', '').strip()
        phonetic = row.get('音标', '').strip()
        definition = row.get('释义', '').strip()

        if not word:
            continue

        # Parse pos from definition (e.g., "n. 艺术" -> pos="n.", def="艺术")
        pos = 'n.'
        clean_def = definition

        pos_match = re.match(r'^([a-z]+\.)\s*(.*)', definition)
        if pos_match:
            pos = pos_match.group(1)
            clean_def = pos_match.group(2)

        words.append({
            'word': word,
            'phonetic': '/' + phonetic + '/' if phonetic else '',
            'pos': pos,
            'definition': clean_def
        })

    return words


def parse_vocab_with_chapters(file_path, excel_files=None):
    """Parse vocabulary JSON file with chapter/group structure.

    Args:
        file_path: Path to the JSON vocabulary file
        excel_files: List of (chapter_title, excel_path) tuples for chapters to read from Excel
                     instead of JSON (for corrupted/missing data in JSON)
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    chapters = []
    all_words_count = 0
    seen_words = set()

    # Build a set of chapter titles that should be read from Excel
    excel_chapters = {}
    if excel_files:
        for title, path in excel_files:
            if os.path.exists(path):
                excel_chapters[title] = path

    # Add chapters from Excel files first (for corrupted JSON data)
    excel_titles_processed = set()
    if excel_files:
        for excel_title, excel_path in excel_files:
            if excel_path and os.path.exists(excel_path):
                # Find the label from JSON for this chapter
                chapter_label = excel_title
                for group in data:
                    if group.get('label', '') == excel_title or group.get('label', '').replace(' ', '') == excel_title.replace(' ', ''):
                        chapter_label = group.get('label', '')
                        break

                words = parse_first_group_excel(excel_path)
                chapter_words = []
                for word_data in words:
                    word_lower = word_data['word'].lower().strip()
                    if len(word_lower) >= 2 and word_lower not in seen_words:
                        seen_words.add(word_lower)
                        chapter_words.append(word_data)

                if chapter_words:
                    chapters.append({
                        'id': len(chapters) + 1,
                        'title': chapter_label,
                        'word_count': len(chapter_words),
                        'words': chapter_words
                    })
                    all_words_count += len(chapter_words)
                    excel_titles_processed.add(chapter_label)

    for idx, group in enumerate(data):
        label = group.get('label', '')

        # Skip chapters that were already processed from Excel
        if label in excel_titles_processed:
            continue

        word_text = group.get('wordText', '')
        if not word_text or word_text.startswith('数据加载中'):
            continue

        # Split by word entries - handle both single /phonetic/ and double //phonetic// slashes
        entries = re.split(r'\n(?=[a-zA-Z][a-zA-Z\s\-\'\.]*?\s*(?://|/)[^/]+(?://|/))', word_text)

        chapter_words = []
        for entry in entries:
            if not entry.strip():
                continue

            word_data = parse_word_entry(entry)
            if word_data and word_data['word']:
                word_lower = word_data['word'].lower().strip()
                # Skip single char words
                if len(word_lower) < 2:
                    continue
                # Track duplicates globally but add to chapter
                seen_words.add(word_lower)
                chapter_words.append(word_data)

        if chapter_words:
            chapters.append({
                'id': len(chapters) + 1,
                'title': label,
                'word_count': len(chapter_words),
                'words': chapter_words
            })
            all_words_count += len(chapter_words)

    return {
        'chapters': chapters,
        'total_chapters': len(chapters),
        'total_words': all_words_count
    }


def main():
    source_dir = r'C:\Users\12081\Desktop\词库'
    output_dir = 'vocabulary_data'

    os.makedirs(output_dir, exist_ok=True)

    # Parse listening vocabulary (听力高频词)
    print("Parsing listening vocabulary with chapters...")
    listening_data = parse_vocab_with_chapters(
        os.path.join(source_dir, '听力高频词_2026-03-17.json'),
        excel_files=[
            ('答案词10次及以上', os.path.join(source_dir, '听力高频词(含答案词)_答案词10次及以上.xlsx')),
        ]
    )
    print(f"  Found {listening_data['total_chapters']} chapters, {listening_data['total_words']} words")

    # Parse reading vocabulary (阅读高频词)
    print("Parsing reading vocabulary with chapters...")
    reading_data = parse_vocab_with_chapters(
        os.path.join(source_dir, '阅读高频词_2026-03-17.json'),
        excel_files=[
            ('150次及以上', os.path.join(source_dir, '阅读高频词_150次及以上.xlsx')),
            ('120~149次', os.path.join(source_dir, '爱听写阅读高频词_120~149次.xlsx')),
        ]
    )
    print(f"  Found {reading_data['total_chapters']} chapters, {reading_data['total_words']} words")

    # Save listening vocabulary
    listening_output = os.path.join(output_dir, 'ielts_listening_premium.json')
    with open(listening_output, 'w', encoding='utf-8') as f:
        json.dump(listening_data, f, ensure_ascii=False, indent=2)
    print(f"  Saved to {listening_output}")

    # Save reading vocabulary
    reading_output = os.path.join(output_dir, 'ielts_reading_premium.json')
    with open(reading_output, 'w', encoding='utf-8') as f:
        json.dump(reading_data, f, ensure_ascii=False, indent=2)
    print(f"  Saved to {reading_output}")

    # Write chapter info to file
    chapter_file = os.path.join(output_dir, '_chapter_info.txt')
    with open(chapter_file, 'w', encoding='utf-8') as f:
        f.write("听力高频词章节:\n")
        for ch in listening_data['chapters']:
            f.write(f"  {ch['id']}. {ch['title']} ({ch['word_count']}词)\n")

        f.write("\n\n阅读高频词章节:\n")
        for ch in reading_data['chapters']:
            f.write(f"  {ch['id']}. {ch['title']} ({ch['word_count']}词)\n")

    print(f"  Chapter info written to {chapter_file}")


if __name__ == '__main__':
    main()