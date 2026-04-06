def pronunciation_check_response(current_user, body):
    ai = _ai_module()
    import logging

    body = body or {}
    word = str(body.get('word') or '').strip()
    transcript = str(body.get('transcript') or '').strip()
    sentence = str(body.get('sentence') or '').strip()
    book_id = str(body.get('bookId') or '').strip() or None
    chapter_id = ai._normalize_chapter_id(body.get('chapterId'))
    if not word:
        return ai.jsonify({'error': 'word is required'}), 400

    score = 85 if transcript.lower() == word.lower() else 65
    passed = score >= 80
    result = {
        'word': word,
        'score': score,
        'passed': passed,
        'stress_feedback': '重音位置基本正确，建议再拉长重读音节。',
        'vowel_feedback': '元音饱满度中等，可再放慢语速。',
        'speed_feedback': '语速可接受，注意词尾清晰度。',
    }
    try:
        ai.record_learning_event(
            user_id=current_user.id,
            event_type='pronunciation_check',
            source='assistant',
            mode='speaking',
            book_id=book_id,
            chapter_id=chapter_id,
            word=word,
            item_count=1,
            correct_count=1 if passed else 0,
            wrong_count=0 if passed else 1,
            payload={
                'score': score,
                'passed': passed,
                'transcript': transcript[:160],
                'sentence': sentence[:300] if sentence else None,
            },
        )
        ai.db.session.commit()
    except Exception as exc:
        ai.db.session.rollback()
        logging.warning("[AI] Failed to record pronunciation check: %s", exc)
    ai._track_metric(current_user.id, 'pronunciation_check_used', {'word': word, 'score': score})
    return ai.jsonify(result), 200


def speaking_simulate_response(current_user, body):
    ai = _ai_module()
    import logging

    body = body or {}
    part = int(body.get('part', 1))
    topic = str(body.get('topic') or 'education').strip()
    target_words = ai._normalize_word_list(
        body.get('targetWords')
        or body.get('target_words')
        or body.get('words')
        or body.get('word')
    )
    response_text = str(
        body.get('responseText')
        or body.get('response_text')
        or body.get('transcript')
        or ''
    ).strip()
    book_id = str(body.get('bookId') or '').strip() or None
    chapter_id = ai._normalize_chapter_id(body.get('chapterId'))
    question_map = {
        1: f"Part 1: Do you enjoy learning vocabulary about {topic}?",
        2: f"Part 2: Describe a time when {topic} vocabulary helped your IELTS performance.",
        3: f"Part 3: How can schools improve students' {topic} related lexical resources?",
    }
    question = question_map.get(part, question_map[1])
    try:
        ai.record_learning_event(
            user_id=current_user.id,
            event_type='speaking_simulation',
            source='assistant',
            mode='speaking',
            book_id=book_id,
            chapter_id=chapter_id,
            word=target_words[0] if len(target_words) == 1 else None,
            item_count=max(1, len(target_words)),
            correct_count=1 if response_text else 0,
            wrong_count=0,
            payload={
                'part': part,
                'topic': topic,
                'question': question,
                'target_words': target_words,
                'response_text': response_text[:500] if response_text else None,
            },
        )
        ai.db.session.commit()
    except Exception as exc:
        ai.db.session.rollback()
        logging.warning("[AI] Failed to record speaking simulation: %s", exc)
    ai._track_metric(current_user.id, 'speaking_simulation_used', {'part': part, 'topic': topic})
    return ai.jsonify({
        'part': part,
        'topic': topic,
        'question': question,
        'follow_ups': ['请给出一个具体例子。', '能否用更学术的表达重述？'],
    }), 200


def review_plan_response(current_user):
    ai = _ai_module()
    profile = ai.build_learner_profile(current_user.id)
    memory_system = profile.get('memory_system') or {}
    dimensions = memory_system.get('dimensions') or []
    plan = profile.get('next_actions') or []
    if not plan:
        plan = ['先补当前优先维度 10 分钟，再安排错词辨析和巩固复现。']

    response = {
        'level': 'four-dimensional',
        'wrong_words': ai.UserWrongWord.query.filter_by(user_id=current_user.id).count(),
        'mastery_rule': memory_system.get('mastery_rule'),
        'priority_dimension': memory_system.get('priority_dimension_label'),
        'priority_reason': memory_system.get('priority_reason'),
        'plan': plan[:4],
        'dimensions': [
            {
                'key': item.get('key'),
                'label': item.get('label'),
                'status': item.get('status'),
                'status_label': item.get('status_label'),
                'schedule_label': item.get('schedule_label'),
                'next_action': item.get('next_action'),
            }
            for item in dimensions
        ],
    }
    ai._track_metric(
        current_user.id,
        'adaptive_plan_generated',
        {
            'level': 'four-dimensional',
            'priority_dimension': memory_system.get('priority_dimension'),
        },
    )
    return ai.jsonify(response), 200


def vocab_assessment_response(current_user, args):
    ai = _ai_module()
    count = min(max(int(args.get('count', 20)), 5), 50)
    pool = ai._get_global_vocab_pool()
    ai.random.shuffle(pool)
    questions = [{
        'word': word.get('word'),
        'definition': word.get('definition'),
        'pos': word.get('pos'),
    } for word in pool[:count]]
    ai._track_metric(current_user.id, 'vocab_assessment_generated', {'count': count})
    return ai.jsonify({'count': len(questions), 'questions': questions}), 200
