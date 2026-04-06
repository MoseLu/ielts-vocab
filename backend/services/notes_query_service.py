from __future__ import annotations

import re
from datetime import datetime, timedelta
from importlib import import_module


def _notes_module():
    return import_module('routes.notes')


def get_notes_response(user_id: int, args):
    notes = _notes_module()
    per_page, err = notes._parse_int_param(args.get('per_page'), default=20, min_val=1, max_val=100)
    if err:
        return notes.jsonify({'error': err}), 400

    before_id_raw = args.get('before_id')
    before_id = None
    if before_id_raw is not None:
        before_id, err = notes._parse_int_param(
            before_id_raw,
            default=0,
            min_val=1,
            max_val=2_147_483_647,
        )
        if err:
            return notes.jsonify({'error': f'before_id: {err}'}), 400

    start_date, err = notes._parse_date_param(args.get('start_date'), 'start_date')
    if err:
        return notes.jsonify({'error': err}), 400
    end_date, err = notes._parse_date_param(args.get('end_date'), 'end_date')
    if err:
        return notes.jsonify({'error': err}), 400
    if start_date and end_date and start_date > end_date:
        return notes.jsonify({'error': 'start_date 不能晚于 end_date'}), 400

    filtered_query = notes.UserLearningNote.query.filter_by(user_id=user_id)
    if start_date:
        filtered_query = filtered_query.filter(
            notes.UserLearningNote.created_at >= datetime.strptime(start_date, '%Y-%m-%d')
        )
    if end_date:
        filtered_query = filtered_query.filter(
            notes.UserLearningNote.created_at < datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
        )

    memory_source_notes = filtered_query.order_by(notes.UserLearningNote.created_at.desc()).limit(160).all()
    memory_topics = notes.build_memory_topics(memory_source_notes, limit=8, include_singletons=True)

    query = filtered_query
    if before_id:
        query = query.filter(notes.UserLearningNote.id < before_id)

    total = filtered_query.count()
    learning_notes = query.order_by(notes.UserLearningNote.id.desc()).limit(per_page).all()
    has_more = len(learning_notes) == per_page
    next_cursor = learning_notes[-1].id if has_more else None

    return notes.jsonify({
        'notes': [note.to_dict() for note in learning_notes],
        'memory_topics': memory_topics,
        'total': total,
        'per_page': per_page,
        'next_cursor': next_cursor,
        'has_more': has_more,
    })


def get_summaries_response(user_id: int, args):
    notes = _notes_module()
    start_date, err = notes._parse_date_param(args.get('start_date'), 'start_date')
    if err:
        return notes.jsonify({'error': err}), 400
    end_date, err = notes._parse_date_param(args.get('end_date'), 'end_date')
    if err:
        return notes.jsonify({'error': err}), 400
    if start_date and end_date and start_date > end_date:
        return notes.jsonify({'error': 'start_date 不能晚于 end_date'}), 400

    query = notes.UserDailySummary.query.filter_by(user_id=user_id)
    if start_date:
        query = query.filter(notes.UserDailySummary.date >= start_date)
    if end_date:
        query = query.filter(notes.UserDailySummary.date <= end_date)

    summaries = query.order_by(notes.UserDailySummary.date.desc()).all()
    return notes.jsonify({'summaries': [summary.to_dict() for summary in summaries]})


def export_notes_response(user_id: int, args):
    notes = _notes_module()
    start_date, err = notes._parse_date_param(args.get('start_date'), 'start_date')
    if err:
        return notes.jsonify({'error': err}), 400
    end_date, err = notes._parse_date_param(args.get('end_date'), 'end_date')
    if err:
        return notes.jsonify({'error': err}), 400
    if start_date and end_date and start_date > end_date:
        return notes.jsonify({'error': 'start_date 不能晚于 end_date'}), 400

    fmt = args.get('format', 'md')
    if fmt not in ('md', 'txt'):
        fmt = 'md'

    export_type = args.get('type', 'all')
    if export_type not in ('summaries', 'notes', 'all'):
        export_type = 'all'

    sections: list[str] = []
    if export_type in ('summaries', 'all'):
        query = notes.UserDailySummary.query.filter_by(user_id=user_id)
        if start_date:
            query = query.filter(notes.UserDailySummary.date >= start_date)
        if end_date:
            query = query.filter(notes.UserDailySummary.date <= end_date)
        summaries = query.order_by(notes.UserDailySummary.date.asc()).all()
        if summaries:
            sections.append("# 每日学习总结\n")
            for summary in summaries:
                sections.append(f"\n---\n\n{summary.content}\n")

    if export_type in ('notes', 'all'):
        query = notes.UserLearningNote.query.filter_by(user_id=user_id)
        if start_date:
            query = query.filter(notes.UserLearningNote.created_at >= datetime.strptime(start_date, '%Y-%m-%d'))
        if end_date:
            query = query.filter(
                notes.UserLearningNote.created_at < datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
            )
        learning_notes = query.order_by(notes.UserLearningNote.created_at.asc()).all()
        if learning_notes:
            sections.append("\n# AI 问答笔记\n")
            current_day = None
            for note in learning_notes:
                day = note.created_at.strftime('%Y-%m-%d') if note.created_at else '未知日期'
                if day != current_day:
                    current_day = day
                    sections.append(f"\n## {day}\n")
                word_info = f"（{note.word_context}）" if note.word_context else ""
                sections.append(f"\n**问：** {note.question}{word_info}\n\n**答：** {note.answer}\n")

    content = '\n'.join(sections) if sections else "暂无数据。"
    if fmt == 'txt':
        content = re.sub(r'#{1,6}\s*', '', content)
        content = re.sub(r'\*{1,2}(.+?)\*{1,2}', r'\1', content)
        content = re.sub(r'\n{3,}', '\n\n', content)

    date_range = f"{start_date or 'all'}_{end_date or 'all'}"
    filename = f"ielts_notes_{date_range}.{'md' if fmt != 'txt' else 'txt'}"
    return notes.jsonify({
        'content': content,
        'filename': filename,
        'format': fmt,
    })
