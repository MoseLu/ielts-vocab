from __future__ import annotations

from collections import defaultdict

from platform_sdk.learning_repository_adapters import learning_stats_repository
from platform_sdk.learner_profile_builder_adapter import build_learner_profile


def build_context_data(
    user_id: int,
    *,
    alltime_words_display_resolver,
    load_memory_resolver,
    load_vocab_books,
    serialize_effective_book_progress,
) -> dict:
    book_progress = learning_stats_repository.list_user_book_progress_rows(user_id)
    chapter_progress = learning_stats_repository.list_user_chapter_progress_rows(user_id)
    wrong_words = learning_stats_repository.list_user_wrong_words_for_ai(
        user_id,
        limit=8,
        recent_first=True,
    )
    recent_sessions = learning_stats_repository.list_user_study_sessions_with_words(
        user_id,
        descending=True,
        limit=20,
    )
    chapter_session_rows = learning_stats_repository.list_user_study_sessions_with_words(
        user_id,
        descending=True,
        limit=200,
    )

    chapter_sessions: dict[str, list[UserStudySession]] = defaultdict(list)
    for session in chapter_session_rows:
        key = f'{session.book_id}__{session.chapter_id}'
        chapter_sessions[key].append(session)

    vocab_books = load_vocab_books() or []
    book_title_map = {book['id']: book['title'] for book in vocab_books}
    chapter_session_stats = {}
    for key, sessions in chapter_sessions.items():
        book_id, chapter_id = key.split('__', 1)
        ordered = sorted(sessions, key=lambda session: session.started_at or 0)
        accuracies = [
            round(session.correct_count / session.words_studied * 100)
            for session in ordered
            if session.words_studied > 0
        ]
        if len(accuracies) >= 2:
            mid = max(1, len(accuracies) // 2)
            early_avg = sum(accuracies[:mid]) / mid
            late_avg = sum(accuracies[mid:]) / max(len(accuracies) - mid, 1)
            trend = (
                '↑进步'
                if late_avg - early_avg >= 5
                else '↓下滑' if early_avg - late_avg >= 5 else '→稳定'
            )
        else:
            trend = '—'
        total_words = sum(session.words_studied for session in sessions)
        avg_accuracy = round(sum(accuracies) / len(accuracies)) if accuracies else 0
        chapter_session_stats[key] = {
            'book_id': book_id,
            'chapter_id': chapter_id,
            'book_title': book_title_map.get(book_id, book_id),
            'session_count': len(sessions),
            'total_words': total_words,
            'avg_accuracy': avg_accuracy,
            'accuracies': accuracies,
            'trend': trend,
            'modes': list({session.mode for session in sessions if session.mode}),
        }

    books = []
    total_effective_words = 0
    total_correct = 0
    total_wrong = 0

    book_progress_by_id = {
        progress.book_id: progress
        for progress in book_progress
        if progress.book_id
    }
    chapter_progress_by_book: dict[str, list[UserChapterProgress]] = defaultdict(list)
    for progress in chapter_progress:
        if progress.book_id:
            chapter_progress_by_book[progress.book_id].append(progress)

    book_word_count_map = {
        book['id']: book.get('word_count', 0)
        for book in vocab_books
    }
    all_book_ids = sorted(set(book_progress_by_id) | set(chapter_progress_by_book))
    for book_id in all_book_ids:
        effective = serialize_effective_book_progress(
            book_id,
            progress_record=book_progress_by_id.get(book_id),
            chapter_records=chapter_progress_by_book.get(book_id, []),
        )
        if not effective:
            continue

        correct_count = int(effective.get('correct_count') or 0)
        wrong_count = int(effective.get('wrong_count') or 0)
        attempted = correct_count + wrong_count
        word_count = int(book_word_count_map.get(book_id, 0) or 0)
        current_index = int(effective.get('current_index') or 0)

        total_effective_words += current_index
        total_correct += correct_count
        total_wrong += wrong_count

        books.append({
            'id': book_id,
            'title': book_title_map.get(book_id, book_id),
            'wordCount': word_count,
            'progress': round(current_index / word_count * 100) if word_count > 0 else 0,
            'accuracy': round(correct_count / attempted * 100) if attempted > 0 else 0,
            'wrongCount': wrong_count,
            'correctCount': correct_count,
        })

    total_learned = alltime_words_display_resolver(user_id, total_effective_words)
    total_attempted = total_correct + total_wrong
    accuracy_rate = round(total_correct / total_attempted * 100) if total_attempted > 0 else 0

    if len(recent_sessions) >= 4:
        mid = len(recent_sessions) // 2
        newer = recent_sessions[:mid]
        older = recent_sessions[mid:]

        def _avg_acc(sessions):
            items = [session for session in sessions if session.words_studied > 0]
            if not items:
                return 0
            return sum(session.correct_count / session.words_studied for session in items) / len(items)

        trend = (
            'improving'
            if _avg_acc(newer) > _avg_acc(older) + 0.05
            else 'declining' if _avg_acc(newer) < _avg_acc(older) - 0.05 else 'stable'
        )
    elif recent_sessions:
        trend = 'stable'
    else:
        recent_chapter_progress = learning_stats_repository.list_user_chapter_progress_rows(
            user_id,
            order_by_updated=True,
            descending=True,
            limit=5,
        )
        if len(recent_chapter_progress) >= 2:
            first_half = sum(
                progress.correct_count / max(progress.correct_count + progress.wrong_count, 1)
                for progress in recent_chapter_progress[len(recent_chapter_progress) // 2:]
            )
            second_half = sum(
                progress.correct_count / max(progress.correct_count + progress.wrong_count, 1)
                for progress in recent_chapter_progress[:len(recent_chapter_progress) // 2]
            )
            trend = (
                'improving'
                if second_half > first_half
                else 'declining' if second_half < first_half else 'stable'
            )
        else:
            trend = 'new'

    recent_sessions_data = []
    for session in recent_sessions[:10]:
        accuracy = round(session.correct_count / session.words_studied * 100) if session.words_studied else 0
        recent_sessions_data.append({
            'mode': session.mode,
            'book_id': session.book_id,
            'chapter_id': session.chapter_id,
            'book_title': book_title_map.get(session.book_id or '', session.book_id or ''),
            'words_studied': session.words_studied,
            'correct_count': session.correct_count,
            'wrong_count': session.wrong_count,
            'accuracy': accuracy,
            'duration_seconds': session.duration_seconds,
            'started_at': session.started_at.isoformat() if session.started_at else None,
        })

    memory = load_memory_resolver(user_id)
    learner_profile = build_learner_profile(user_id)

    return {
        'totalBooks': len(books),
        'totalLearned': total_learned,
        'totalCorrect': total_correct,
        'totalWrong': total_wrong,
        'accuracyRate': accuracy_rate,
        'books': books,
        'wrongWords': [
            {
                'word': word.word,
                'phonetic': word.phonetic,
                'pos': word.pos,
                'definition': word.definition,
                'wrongCount': word.wrong_count,
                'updatedAt': word.updated_at.isoformat() if word.updated_at else None,
            }
            for word in wrong_words
        ],
        'recentTrend': trend,
        'recentSessions': recent_sessions_data,
        'chapterSessionStats': list(chapter_session_stats.values()),
        'totalSessions': len(recent_sessions),
        'learnerProfile': learner_profile,
        'activityTimeline': {
            'summary': learner_profile.get('activity_summary') or {},
            'source_breakdown': learner_profile.get('activity_source_breakdown') or [],
            'event_breakdown': learner_profile.get('activity_event_breakdown') or [],
            'recent_events': learner_profile.get('recent_activity') or [],
        },
        'memory': memory,
    }
