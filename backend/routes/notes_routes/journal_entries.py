"""Journal note entry CRUD and AI polish endpoints."""

from datetime import datetime

from flask import jsonify, request

from models import UserJournalNote, db
from routes.middleware import token_required
from services.journal_polish_service import JournalPolishUnavailable, polish_text


def _today_str() -> str:
    return datetime.utcnow().strftime('%Y-%m-%d')


def _parse_date(value: str | None) -> str | None:
    if not value or not value.strip():
        return None
    return value.strip()


@notes_bp.route('/journal', methods=['GET'])
@token_required
def list_journal_entries(current_user):
    """List journal entries with cursor pagination and optional date filters."""
    per_page = request.args.get('per_page', 10, type=int)
    before_id = request.args.get('before_id', type=int)
    start_date = _parse_date(request.args.get('start_date'))
    end_date = _parse_date(request.args.get('end_date'))

    query = UserJournalNote.query.filter_by(user_id=current_user.id)

    if start_date:
        query = query.filter(UserJournalNote.date >= start_date)
    if end_date:
        query = query.filter(UserJournalNote.date <= end_date)
    if before_id:
        query = query.filter(UserJournalNote.id < before_id)

    query = query.order_by(UserJournalNote.id.desc())

    entries = query.limit(per_page + 1).all()
    has_more = len(entries) > per_page
    if has_more:
        entries = entries[:per_page]

    return jsonify({
        'entries': [e.to_dict() for e in entries],
        'has_more': has_more,
    })


@notes_bp.route('/journal/today', methods=['GET'])
@token_required
def get_today_journal(current_user):
    """Get today's journal entry, or null if none exists."""
    today = _today_str()
    entry = UserJournalNote.query.filter_by(
        user_id=current_user.id, date=today
    ).first()

    return jsonify({
        'entry': entry.to_dict() if entry else None,
    })


@notes_bp.route('/journal', methods=['POST'])
@token_required
def upsert_journal_entry(current_user):
    """Create or update today's journal entry."""
    body = request.get_json(silent=True) or {}
    content = (body.get('content') or '').strip()

    if not content:
        return jsonify({'error': '内容不能为空'}), 400

    today = _today_str()
    entry = UserJournalNote.query.filter_by(
        user_id=current_user.id, date=today
    ).first()

    if entry:
        entry.content = content
        entry.updated_at = datetime.utcnow()
    else:
        entry = UserJournalNote(
            user_id=current_user.id,
            date=today,
            content=content,
        )
        db.session.add(entry)

    db.session.commit()

    return jsonify({
        'entry': entry.to_dict(),
    })


@notes_bp.route('/journal/polish', methods=['POST'])
@token_required
def polish_journal_entry(current_user):
    """Polish the given markdown content using AI."""
    body = request.get_json(silent=True) or {}
    content = (body.get('content') or '').strip()

    if not content:
        return jsonify({'error': '内容不能为空'}), 400

    try:
        polished = polish_text(content)
    except JournalPolishUnavailable as exc:
        return jsonify({'error': str(exc)}), 503

    return jsonify({
        'polished': polished,
    })
