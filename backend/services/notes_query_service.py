from __future__ import annotations

import re
from datetime import datetime, timedelta

from flask import jsonify

from runtime_paths import ensure_shared_package_paths
from services import daily_summary_repository, learning_note_repository
from services.memory_topics import build_memory_topics
from services.notes_summary_service import parse_date_param, parse_int_param

ensure_shared_package_paths()

from platform_sdk.notes_export_storage import store_notes_export


def get_notes_response(user_id: int, args):
    per_page, err = parse_int_param(args.get('per_page'), default=20, min_val=1, max_val=100)
    if err:
        return jsonify({'error': err}), 400

    before_id_raw = args.get('before_id')
    before_id = None
    if before_id_raw is not None:
        before_id, err = parse_int_param(
            before_id_raw,
            default=0,
            min_val=1,
            max_val=2_147_483_647,
        )
        if err:
            return jsonify({'error': f'before_id: {err}'}), 400

    start_date, err = parse_date_param(args.get('start_date'), 'start_date')
    if err:
        return jsonify({'error': err}), 400
    end_date, err = parse_date_param(args.get('end_date'), 'end_date')
    if err:
        return jsonify({'error': err}), 400
    if start_date and end_date and start_date > end_date:
        return jsonify({'error': 'start_date 不能晚于 end_date'}), 400

    start_dt = datetime.strptime(start_date, '%Y-%m-%d') if start_date else None
    end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1) if end_date else None

    memory_source_notes = learning_note_repository.list_learning_notes(
        user_id,
        start_at=start_dt,
        end_before=end_dt,
        descending=True,
        order_by='created_at',
        limit=160,
    )
    memory_topics = build_memory_topics(memory_source_notes, limit=8, include_singletons=True)

    total = learning_note_repository.count_learning_notes(
        user_id,
        start_at=start_dt,
        end_before=end_dt,
    )
    learning_notes = learning_note_repository.list_learning_notes(
        user_id,
        start_at=start_dt,
        end_before=end_dt,
        before_id=before_id,
        descending=True,
        order_by='id',
        limit=per_page,
    )
    has_more = len(learning_notes) == per_page
    next_cursor = learning_notes[-1].id if has_more else None

    return jsonify({
        'notes': [note.to_dict() for note in learning_notes],
        'memory_topics': memory_topics,
        'total': total,
        'per_page': per_page,
        'next_cursor': next_cursor,
        'has_more': has_more,
    })


def get_summaries_response(user_id: int, args):
    start_date, err = parse_date_param(args.get('start_date'), 'start_date')
    if err:
        return jsonify({'error': err}), 400
    end_date, err = parse_date_param(args.get('end_date'), 'end_date')
    if err:
        return jsonify({'error': err}), 400
    if start_date and end_date and start_date > end_date:
        return jsonify({'error': 'start_date 不能晚于 end_date'}), 400

    summaries = daily_summary_repository.list_daily_summaries(
        user_id,
        start_date=start_date,
        end_date=end_date,
        descending=True,
    )
    return jsonify({'summaries': [summary.to_dict() for summary in summaries]})


def export_notes_response(user_id: int, args):
    start_date, err = parse_date_param(args.get('start_date'), 'start_date')
    if err:
        return jsonify({'error': err}), 400
    end_date, err = parse_date_param(args.get('end_date'), 'end_date')
    if err:
        return jsonify({'error': err}), 400
    if start_date and end_date and start_date > end_date:
        return jsonify({'error': 'start_date 不能晚于 end_date'}), 400

    fmt = args.get('format', 'md')
    if fmt not in ('md', 'txt'):
        fmt = 'md'

    export_type = args.get('type', 'all')
    if export_type not in ('summaries', 'notes', 'all'):
        export_type = 'all'

    sections: list[str] = []
    if export_type in ('summaries', 'all'):
        summaries = daily_summary_repository.list_daily_summaries(
            user_id,
            start_date=start_date,
            end_date=end_date,
            descending=False,
        )
        if summaries:
            sections.append("# 每日学习总结\n")
            for summary in summaries:
                sections.append(f"\n---\n\n{summary.content}\n")

    if export_type in ('notes', 'all'):
        learning_notes = learning_note_repository.list_learning_notes(
            user_id,
            start_at=datetime.strptime(start_date, '%Y-%m-%d') if start_date else None,
            end_before=datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1) if end_date else None,
            descending=False,
            order_by='created_at',
        )
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
    export_storage = store_notes_export(
        user_id=user_id,
        filename=filename,
        fmt=fmt,
        content=content,
    )
    return jsonify({
        'content': content,
        'filename': filename,
        'format': fmt,
        **export_storage,
    })
