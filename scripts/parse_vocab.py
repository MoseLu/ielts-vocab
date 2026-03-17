#!/usr/bin/env python3
"""
Parse vocabulary files from desktop and convert to standard format.
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

    # Pattern: word /phonetic/ (with possible trailing content)
    # e.g., "car /kɑː(r)/" or "art/ɑːt/n. 艺术词根词缀..."
    match = re.match(r'^([a-zA-Z][a-zA-Z\s\-\'\.]*?)\s*/([^/]+)/?(.*)$', first_line)
    if match:
        result['word'] = match.group(1).strip()
        result['phonetic'] = '/' + match.group(2) + '/'
        trailing = match.group(3).strip()

        # Check if trailing has pos.definition pattern
        if trailing:
            pos_match = re.match(r'^([a-z]+\.)\s*(.*)', trailing)
            if pos_match:
                result['pos'] = pos_match.group(1)
                # Don't include word root info in definition
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
                # Update pos if still default
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
            # Combine definitions, clean up
            def_text = '；'.join([d.rstrip('；;') for d in definitions[:3] if d])
            # Remove duplicate info
            result['definition'] = re.sub(r'["""].*["""]', '', def_text).strip()

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


def parse_vocab_json(file_path, skip_labels=None):
    """Parse vocabulary JSON file."""
    if skip_labels is None:
        skip_labels = []

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    all_words = []
    seen_words = set()

    for group in data:
        label = group.get('label', '')
        # Skip certain groups (like the first special entry)
        if any(skip in label for skip in skip_labels):
            continue

        word_text = group.get('wordText', '')
        if not word_text or word_text.startswith('数据加载中'):
            continue

        # Split by word entries - look for pattern: newline followed by word then /phonetic/
        # Pattern: \n followed by word, optional space, then /phonetic/
        entries = re.split(r'\n(?=[a-zA-Z][a-zA-Z\s\-\'\.]*?\s*/[^/]+/)', word_text)

        for entry in entries:
            if not entry.strip():
                continue

            word_data = parse_word_entry(entry)
            if word_data and word_data['word']:
                word_lower = word_data['word'].lower().strip()
                # Skip single char words
                if len(word_lower) < 2:
                    continue
                if word_lower not in seen_words:
                    seen_words.add(word_lower)
                    all_words.append(word_data)

    return all_words


def main():
    source_dir = r'C:\Users\12081\Desktop\词库'
    output_dir = 'vocabulary_data'

    os.makedirs(output_dir, exist_ok=True)

    # Parse listening vocabulary (听力高频词)
    print("Parsing listening vocabulary...")
    listening_words = parse_vocab_json(
        os.path.join(source_dir, '听力高频词_2026-03-17.json'),
        skip_labels=['答案词10次及以上']  # Skip first malformed group
    )
    print(f"  Found {len(listening_words)} unique words")

    # Parse dictation vocabulary (爱听写高频词)
    print("Parsing dictation vocabulary...")
    dictation_words = parse_vocab_json(
        os.path.join(source_dir, '爱听写高频词_2026-03-17.json'),
        skip_labels=['150次及以上']  # Skip first malformed group
    )
    print(f"  Found {len(dictation_words)} unique words")

    # Save listening vocabulary
    listening_output = os.path.join(output_dir, 'ielts_listening_premium.json')
    with open(listening_output, 'w', encoding='utf-8') as f:
        json.dump(listening_words, f, ensure_ascii=False, indent=2)
    print(f"  Saved to {listening_output}")

    # Save dictation vocabulary
    dictation_output = os.path.join(output_dir, 'ielts_dictation_premium.json')
    with open(dictation_output, 'w', encoding='utf-8') as f:
        json.dump(dictation_words, f, ensure_ascii=False, indent=2)
    print(f"  Saved to {dictation_output}")

    # Write sample to file (avoid encoding issues in terminal)
    sample_file = os.path.join(output_dir, '_sample_output.txt')
    with open(sample_file, 'w', encoding='utf-8') as f:
        f.write("Sample words from listening vocabulary:\n")
        for w in listening_words[:10]:
            f.write(f"  {w['word']} {w['phonetic']} {w['pos']} {w['definition'][:40]}...\n")
        f.write("\nSample words from dictation vocabulary:\n")
        for w in dictation_words[:10]:
            f.write(f"  {w['word']} {w['phonetic']} {w['pos']} {w['definition'][:40]}...\n")
    print(f"  Sample output written to {sample_file}")


if __name__ == '__main__':
    main()