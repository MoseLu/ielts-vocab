def ielts_example_response(current_user, args):
    ai = _ai_module()
    word = str(args.get('word') or '').strip().lower()
    if not word:
        return ai.jsonify({'error': 'word is required'}), 400
    corpus = ai._load_json_data('ielts-reading-corpus.json', {})
    topic_map = ai._load_json_data('ielts-topics.json', {})
    items = corpus.get(word, [])
    if items:
        ai._track_metric(current_user.id, 'ielts_example_hit', {'word': word, 'count': len(items)})
        return ai.jsonify({'word': word, 'source': 'ielts-corpus', 'examples': items[:5]}), 200
    summary = ai.web_search(f"{word} IELTS reading sentence examples")
    fallback = [{
        'sentence': summary.split('\n')[0][:220],
        'source': 'web_search',
        'topic': topic_map.get(word, 'general'),
        'is_real_exam': False,
    }]
    ai._track_metric(current_user.id, 'ielts_example_fallback', {'word': word})
    return ai.jsonify({'word': word, 'source': 'fallback', 'examples': fallback}), 200


def synonyms_diff_response(current_user, body):
    ai = _ai_module()
    body = body or {}
    word_a = str(body.get('a') or '').strip()
    word_b = str(body.get('b') or '').strip()
    if not word_a or not word_b:
        return ai.jsonify({'error': 'a and b are required'}), 400
    result = ai.differentiate_synonyms(word_a, word_b)
    ai._track_metric(current_user.id, 'synonyms_diff_used', {'pair': f'{word_a}-{word_b}'})
    return ai.jsonify(result), 200


def word_family_response(current_user, args):
    ai = _ai_module()
    word = str(args.get('word') or '').strip().lower()
    if not word:
        return ai.jsonify({'error': 'word is required'}), 400
    db_json = ai._load_json_data('word-families.json', {})
    data = db_json.get(word)
    if not data:
        return ai.jsonify({
            'word': word,
            'message': '暂未收录该词族，建议查询实义词（如 establish / analyze / regulate）。',
        }), 200
    ai._track_metric(current_user.id, 'word_family_used', {'word': word})
    return ai.jsonify(data), 200


def word_family_quiz_response(current_user, args):
    ai = _ai_module()
    word = str(args.get('word') or '').strip().lower()
    data = ai._load_json_data('word-families.json', {}).get(word, {})
    variants = data.get('variants', [])
    if len(variants) < 2:
        return ai.jsonify({'error': 'not enough variants'}), 400
    picked = ai.random.choice(variants)
    others = [item.get('word') for item in variants if item.get('word') and item.get('word') != picked.get('word')]
    return ai.jsonify({
        'prompt': f"请说出与 {picked.get('word')} 同词族的另外两个词",
        'answer_candidates': others[:4],
        'analysis': f"{picked.get('word')} 属于 {word} 词族，注意词性转换。",
    }), 200


def collocation_practice_response(current_user, args):
    ai = _ai_module()
    topic = str(args.get('topic') or 'general').strip().lower()
    mode = str(args.get('mode') or 'mcq').strip().lower()
    count = min(max(int(args.get('count', 5)), 1), 20)
    pool = ai._load_json_data('ielts-collocations.json', [])
    filtered = [item for item in pool if item.get('topic', 'general') in (topic, 'general')] or pool
    ai.random.shuffle(filtered)
    ai._track_metric(current_user.id, 'collocation_practice_used', {'topic': topic, 'mode': mode, 'count': count})
    return ai.jsonify({'topic': topic, 'mode': mode, 'items': filtered[:count]}), 200
