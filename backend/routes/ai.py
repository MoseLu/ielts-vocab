import re
import json
import uuid
import os
import random
import functools
import time
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request
from sqlalchemy import text
from models import db, User, UserBookProgress, UserChapterProgress, UserChapterModeProgress, CustomBook, CustomBookChapter, CustomBookWord, UserWrongWord, UserStudySession, UserQuickMemoryRecord, UserSmartWordStat, UserConversationHistory, UserMemory, UserLearningNote
from routes.middleware import token_required
from services.learner_profile import build_learner_profile
from services.memory_topics import build_memory_topics
from services.llm import chat, web_search, TOOLS, TOOL_HANDLERS, correct_text, differentiate_synonyms

ai_bp = Blueprint('ai', __name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')


def _load_json_data(filename: str, default):
    path = os.path.join(DATA_DIR, filename)
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return default


def _track_metric(user_id: int, metric: str, payload: dict | None = None):
    """轻量埋点：先写日志，后续可切换独立事件表。"""
    import logging
    logging.info("[AI_METRIC] user=%s metric=%s payload=%s", user_id, metric, payload or {})


def _alltime_distinct_practiced_words(user_id: int) -> int:
    """全局去重词数：智能/速记/错词本等表里的 word 并集（跨书、跨章只计一次）。

    user_chapter_progress.words_learned 按章相加会把跨章重复词算多次，也可能存过「答题次数」；
    该值用于在明显虚高时收敛统计。
    """
    try:
        r = db.session.execute(
            text(
                """
                SELECT COUNT(*) FROM (
                    SELECT LOWER(TRIM(word)) AS w FROM user_smart_word_stats
                    WHERE user_id = :uid AND word IS NOT NULL AND TRIM(word) != ''
                    UNION
                    SELECT LOWER(TRIM(word)) FROM user_quick_memory_records
                    WHERE user_id = :uid AND word IS NOT NULL AND TRIM(word) != ''
                    UNION
                    SELECT LOWER(TRIM(word)) FROM user_wrong_words
                    WHERE user_id = :uid AND word IS NOT NULL AND TRIM(word) != ''
                )
                """
            ),
            {'uid': user_id},
        ).scalar()
        return int(r or 0)
    except Exception:
        return 0


def _alltime_words_display(user_id: int, chapter_words_sum: int) -> int:
    """累计「学习词数」：章节 words_learned 之和与全局去重并集取合理值。

    章节按章相加会跨章重复计词；若明显高于去重表（>=120%）则采用去重结果。
    使用 >= 避免恰为 1.2 倍时仍走 max 把虚高章节和再展示出去。
    """
    distinct = _alltime_distinct_practiced_words(user_id)
    if distinct <= 0:
        return int(chapter_words_sum or 0)
    # 浮点边界：用整数比较 chapter*10 >= distinct*12
    if chapter_words_sum * 10 >= distinct * 12:
        return distinct
    return max(int(chapter_words_sum or 0), distinct)


def _chapter_title_map(book_id: str) -> dict:
    """chapter_id(str) -> title"""
    try:
        from routes.books import load_book_chapters
        data = load_book_chapters(book_id)
        if not data or not data.get('chapters'):
            return {}
        return {str(c['id']): (c.get('title') or '') for c in data['chapters']}
    except Exception:
        return {}


def _calc_streak_days(user_id: int) -> int:
    """计算用户连续学习天数（基于 UserStudySession）。"""
    sessions = UserStudySession.query.filter_by(user_id=user_id).filter(
        UserStudySession.words_studied > 0
    ).order_by(UserStudySession.started_at.desc()).all()

    if not sessions:
        return 0

    from datetime import timedelta
    date_set: set[str] = set()
    for s in sessions:
        if s.started_at:
            date_set.add(s.started_at.strftime('%Y-%m-%d'))

    if not date_set:
        return 0

    sorted_dates = sorted(date_set, reverse=True)
    today_str = datetime.utcnow().strftime('%Y-%m-%d')
    yesterday_str = (datetime.utcnow() - timedelta(days=1)).strftime('%Y-%m-%d')

    if sorted_dates[0] not in (today_str, yesterday_str):
        return 0

    streak = 0
    current = datetime.strptime(sorted_dates[0], '%Y-%m-%d')
    for date_str in sorted_dates:
        d = datetime.strptime(date_str, '%Y-%m-%d')
        diff = (current - d).days
        if diff <= 1:
            streak += 1
            current = d
        else:
            break
    return streak


def _quick_memory_word_stats(user_id: int):
    """速记(艾宾浩斯)表：今日新词/今日复习/累计复习词数、艾宾浩斯达成率等。"""
    now_utc = datetime.utcnow()
    today_start = datetime(now_utc.year, now_utc.month, now_utc.day)
    today_start_ms = int(today_start.timestamp() * 1000)
    tomorrow_ms = int((today_start + timedelta(days=1)).timestamp() * 1000)
    now_ms = int(now_utc.timestamp() * 1000)

    qm_rows = UserQuickMemoryRecord.query.filter_by(user_id=user_id).all()
    today_new = 0
    today_review = 0
    alltime_review_words = 0  # 至少有过第 2 次作答的词（视为进入复习）
    cumulative_review_events = 0

    for r in qm_rows:
        fs = r.first_seen or 0
        ls = r.last_seen or 0
        kc = r.known_count or 0
        uc = r.unknown_count or 0
        fz = r.fuzzy_count or 0
        if today_start_ms <= fs < tomorrow_ms:
            today_new += 1
        if today_start_ms <= ls < tomorrow_ms and fs < today_start_ms:
            today_review += 1
        if kc + uc >= 2:
            alltime_review_words += 1
        cumulative_review_events += max(0, kc + uc - 1) + fz

    # 艾宾浩斯：已到 next_review 时间点的词中，last_seen 已晚于或等于计划复习时间的占比
    due_met = 0
    due_total = 0
    for r in qm_rows:
        nr = r.next_review or 0
        if nr <= 0:
            continue
        if nr <= now_ms:
            due_total += 1
            ls = r.last_seen or 0
            if ls >= nr:
                due_met += 1
    ebbinghaus_rate = round(due_met / due_total * 100) if due_total > 0 else None

    # 按 known_count 分桶（对应 1/1/4/7/14/30 天间隔轮次）：到期词中各轮「按时回顾」占比
    review_intervals = (1, 1, 4, 7, 14, 30)
    stage_due = [0] * 6
    stage_met = [0] * 6
    for r in qm_rows:
        nr = r.next_review or 0
        if nr <= 0 or nr > now_ms:
            continue
        kc = r.known_count or 0
        stage = min(max(kc, 0), 5)
        stage_due[stage] += 1
        ls = r.last_seen or 0
        if ls >= nr:
            stage_met[stage] += 1
    ebbinghaus_stages = []
    for i in range(6):
        dt = stage_due[i]
        dm = stage_met[i]
        ebbinghaus_stages.append({
            'stage': i,
            'interval_days': review_intervals[i],
            'due_total': dt,
            'due_met': dm,
            'actual_pct': round(dm / dt * 100) if dt > 0 else None,
        })

    # 3天内待复习词数（包含已到期但未复习的）
    upcoming_reviews_3d = 0
    three_days_ms = 3 * 86400000
    for r in qm_rows:
        nr = r.next_review or 0
        if nr > 0 and nr <= now_ms + three_days_ms:
            upcoming_reviews_3d += 1

    return {
        'today_new_words': today_new,
        'today_review_words': today_review,
        'alltime_review_words': alltime_review_words,
        'cumulative_review_events': cumulative_review_events,
        'ebbinghaus_rate': ebbinghaus_rate,
        'ebbinghaus_due_total': due_total,
        'ebbinghaus_met': due_met,
        'qm_word_total': len(qm_rows),
        'ebbinghaus_stages': ebbinghaus_stages,
        'upcoming_reviews_3d': upcoming_reviews_3d,
    }


# ── Global vocabulary pool (all books, deduplicated) ─────────────────────────

@functools.lru_cache(maxsize=1)
def _get_global_vocab_pool() -> list:
    """
    Load every word from every book into one flat list.
    Deduplicates by lowercase word string.  Cached after first call.
    Uses lru_cache to prevent memory leaks in multi-worker deployments.
    """
    from routes.books import VOCAB_BOOKS, load_book_vocabulary
    seen: dict[str, dict] = {}
    for book in VOCAB_BOOKS:
        words = load_book_vocabulary(book['id']) or []
        for w in words:
            key = w.get('word', '').strip().lower()
            if key and key not in seen:
                seen[key] = {
                    'word':       w.get('word', '').strip(),
                    'phonetic':   w.get('phonetic', ''),
                    'pos':        w.get('pos', ''),
                    'definition': w.get('definition', ''),
                }
    return list(seen.values())


# ── Similarity helpers ────────────────────────────────────────────────────────

def _levenshtein(a: str, b: str) -> int:
    m, n = len(a), len(b)
    dp = list(range(n + 1))
    for i in range(1, m + 1):
        prev = dp[0]
        dp[0] = i
        for j in range(1, n + 1):
            tmp = dp[j]
            dp[j] = prev if a[i - 1] == b[j - 1] else 1 + min(prev, dp[j], dp[j - 1])
            prev = tmp
    return dp[n]


_IPA_STRIP = re.compile(r'[/\[\]ˈˌ.: ]')


def _confusability_score(
    tw: str, tp: str, tpos: str,
    cw: str, cp: str, cpos: str,
) -> float:
    """Score how confusable candidate (cw) is with target (tw) for listening mode."""
    tw_l, cw_l = tw.lower(), cw.lower()
    score = 0.0

    # Same POS
    if tpos and cpos and tpos == cpos:
        score += 2.0

    # Spelling similarity (normalised Levenshtein)
    sd = _levenshtein(tw_l, cw_l)
    mx = max(len(tw_l), len(cw_l))
    if mx:
        score += (1 - sd / mx) * 5

    # Common prefix
    pfx = 0
    while pfx < len(tw_l) and pfx < len(cw_l) and tw_l[pfx] == cw_l[pfx]:
        pfx += 1
    score += min(pfx * 0.8, 3.0)

    # Common suffix
    sfx = 0
    while sfx < len(tw_l) and sfx < len(cw_l) and tw_l[-(sfx + 1)] == cw_l[-(sfx + 1)]:
        sfx += 1
    score += min(sfx * 0.5, 1.5)

    # Similar length ±2
    if abs(len(tw_l) - len(cw_l)) <= 2:
        score += 0.5

    # Phonetic similarity
    if tp and cp:
        tp_s = _IPA_STRIP.sub('', tp).lower()
        cp_s = _IPA_STRIP.sub('', cp).lower()
        if tp_s and cp_s:
            pd = _levenshtein(tp_s, cp_s)
            mp = max(len(tp_s), len(cp_s))
            if mp:
                score += (1 - pd / mp) * 4

    return score


# ── GET /api/ai/similar-words ─────────────────────────────────────────────────

@ai_bp.route('/similar-words', methods=['GET'])
@token_required
def get_similar_words(current_user: User):
    """
    Return the N most confusable words from the global vocabulary pool.
    Query params:
      word     – target word (required)
      phonetic – IPA string (optional, improves phonetic scoring)
      pos      – part of speech (optional)
      n        – result count (default 10, max 20)
    """
    target_word = (request.args.get('word') or '').strip()
    if not target_word:
        return jsonify({'error': 'word is required'}), 400

    target_phonetic = request.args.get('phonetic', '')
    target_pos      = request.args.get('pos', '')
    n               = min(int(request.args.get('n', 10)), 20)

    pool = _get_global_vocab_pool()
    tw_lower = target_word.lower()

    scored: list[tuple[float, dict]] = []
    for w in pool:
        if w['word'].lower() == tw_lower:
            continue
        s = _confusability_score(
            target_word, target_phonetic, target_pos,
            w['word'], w.get('phonetic', ''), w.get('pos', ''),
        )
        scored.append((s, w))

    scored.sort(key=lambda x: -x[0])
    return jsonify({'words': [w for _, w in scored[:n]]})


# ── GET /api/ai/context ───────────────────────────────────────────────────────

def _get_context_data(user_id: int) -> dict:
    """Return structured learning summary dict for a given user_id."""
    # Book progress
    book_progress = UserBookProgress.query.filter_by(user_id=user_id).all()
    chapter_progress = UserChapterProgress.query.filter_by(user_id=user_id).all()
    wrong_words = UserWrongWord.query.filter_by(user_id=user_id).order_by(
        UserWrongWord.wrong_count.desc()
    ).limit(50).all()

    # ── Recent study sessions (last 20) for AI context ────────────────────────
    recent_sessions = (
        UserStudySession.query
        .filter_by(user_id=user_id)
        .filter(UserStudySession.words_studied > 0)
        .order_by(UserStudySession.started_at.desc())
        .limit(20)
        .all()
    )

    # Per-chapter session stats: session count + accuracy trend (last 5 sessions per chapter)
    from collections import defaultdict
    chapter_sessions: dict = defaultdict(list)
    for s in UserStudySession.query.filter_by(user_id=user_id).filter(UserStudySession.words_studied > 0).order_by(UserStudySession.started_at.desc()).limit(200).all():
        key = f"{s.book_id}__{s.chapter_id}"
        chapter_sessions[key].append(s)

    chapter_session_stats = {}
    from routes.books import VOCAB_BOOKS
    book_title_map = {b['id']: b['title'] for b in VOCAB_BOOKS}

    for key, sessions in chapter_sessions.items():
        book_id, chapter_id = key.split('__', 1)
        # Accuracy per session (oldest → newest)
        ordered = sorted(sessions, key=lambda s: s.started_at or 0)
        accuracies = [
            round(s.correct_count / s.words_studied * 100)
            for s in ordered if s.words_studied > 0
        ]
        # Trend: compare average of first half vs last half
        if len(accuracies) >= 2:
            mid = max(1, len(accuracies) // 2)
            early_avg = sum(accuracies[:mid]) / mid
            late_avg = sum(accuracies[mid:]) / max(len(accuracies) - mid, 1)
            trend = "↑进步" if late_avg - early_avg >= 5 else "↓下滑" if early_avg - late_avg >= 5 else "→稳定"
        else:
            trend = "—"
        total_words = sum(s.words_studied for s in sessions)
        avg_acc = round(sum(accuracies) / len(accuracies)) if accuracies else 0
        chapter_session_stats[key] = {
            'book_id': book_id,
            'chapter_id': chapter_id,
            'book_title': book_title_map.get(book_id, book_id),
            'session_count': len(sessions),
            'total_words': total_words,
            'avg_accuracy': avg_acc,
            'accuracies': accuracies,
            'trend': trend,
            'modes': list({s.mode for s in sessions if s.mode}),
        }

    # Aggregate per-book stats
    books = []
    total_learned = 0
    total_correct = 0
    total_wrong = 0

    book_map = {}
    for bp in book_progress:
        total = bp.correct_count + bp.wrong_count
        accuracy = round(bp.correct_count / total * 100) if total > 0 else 0
        book_map[bp.book_id] = {
            'id': bp.book_id,
            'progress': round(bp.current_index / 100 * 100) if bp.current_index else 0,  # placeholder ratio
            'accuracy': accuracy,
            'wrongCount': bp.wrong_count,
            'correctCount': bp.correct_count,
        }
        total_learned += bp.current_index
        total_correct += bp.correct_count
        total_wrong += bp.wrong_count

    # Enrich with chapter accuracy — also create book entries for books that
    # only have chapter-level progress (no UserBookProgress record yet)
    for cp in chapter_progress:
        if cp.book_id not in book_map:
            book_map[cp.book_id] = {
                'id': cp.book_id,
                'progress': 0,
                'accuracy': 0,
                'wrongCount': 0,
                'correctCount': 0,
            }
        book_map[cp.book_id]['wrongCount'] = (
            book_map[cp.book_id].get('wrongCount', 0) + cp.wrong_count
        )
        book_map[cp.book_id]['correctCount'] = (
            book_map[cp.book_id].get('correctCount', 0) + cp.correct_count
        )
        total_learned += cp.words_learned
        total_correct += cp.correct_count
        total_wrong += cp.wrong_count

    total_attempted = total_correct + total_wrong
    accuracy_rate = round(total_correct / total_attempted * 100) if total_attempted > 0 else 0

    book_word_count_map = {b['id']: b.get('word_count', 0) for b in VOCAB_BOOKS}

    for book_id, stats in book_map.items():
        stats['title'] = book_title_map.get(book_id, book_id)
        stats['wordCount'] = book_word_count_map.get(book_id, 0)
        stats['progress'] = round(stats['correctCount'] / (stats['correctCount'] + stats.get('wrongCount', 0)) * 100) if (stats['correctCount'] + stats.get('wrongCount', 0)) > 0 else 0

    # Recent trend: use actual study sessions (more reliable than chapter progress timestamps)
    if len(recent_sessions) >= 4:
        mid = len(recent_sessions) // 2
        # recent_sessions is newest-first; older sessions = second half
        newer = recent_sessions[:mid]
        older = recent_sessions[mid:]
        def _avg_acc(sessions):
            items = [s for s in sessions if s.words_studied > 0]
            if not items:
                return 0
            return sum(s.correct_count / s.words_studied for s in items) / len(items)
        trend = "improving" if _avg_acc(newer) > _avg_acc(older) + 0.05 else \
                "declining" if _avg_acc(newer) < _avg_acc(older) - 0.05 else "stable"
    elif recent_sessions:
        trend = "stable"
    else:
        # Fall back to chapter progress trend
        recent_cp = UserChapterProgress.query.filter_by(user_id=user_id).order_by(
            UserChapterProgress.updated_at.desc()
        ).limit(5).all()
        if len(recent_cp) >= 2:
            first_half = sum(r.correct_count / max(r.correct_count + r.wrong_count, 1) for r in recent_cp[len(recent_cp)//2:])
            second_half = sum(r.correct_count / max(r.correct_count + r.wrong_count, 1) for r in recent_cp[:len(recent_cp)//2])
            trend = "improving" if second_half > first_half else "declining" if second_half < first_half else "stable"
        else:
            trend = "new"

    # Build serialisable recent-session list
    recent_sessions_data = []
    for s in recent_sessions[:10]:
        acc = round(s.correct_count / s.words_studied * 100) if s.words_studied else 0
        recent_sessions_data.append({
            'mode': s.mode,
            'book_id': s.book_id,
            'chapter_id': s.chapter_id,
            'book_title': book_title_map.get(s.book_id or '', s.book_id or ''),
            'words_studied': s.words_studied,
            'correct_count': s.correct_count,
            'wrong_count': s.wrong_count,
            'accuracy': acc,
            'duration_seconds': s.duration_seconds,
            'started_at': s.started_at.isoformat() if s.started_at else None,
        })

    # Load persistent AI memory for this user
    memory = _load_memory(user_id)

    return {
        'totalBooks': len(book_map),
        'totalLearned': total_learned,
        'totalCorrect': total_correct,
        'totalWrong': total_wrong,
        'accuracyRate': accuracy_rate,
        'books': list(book_map.values()),
        'wrongWords': [
            {
                'word': w.word,
                'phonetic': w.phonetic,
                'pos': w.pos,
                'definition': w.definition,
                'wrongCount': w.wrong_count
            }
            for w in wrong_words
        ],
        'recentTrend': trend,
        'recentSessions': recent_sessions_data,
        'chapterSessionStats': list(chapter_session_stats.values()),
        'totalSessions': len(recent_sessions),
        'learnerProfile': build_learner_profile(user_id),
        'memory': memory,
    }


@ai_bp.route('/context', methods=['GET'])
@token_required
def get_context(current_user: User):
    """Return structured learning summary for AI context."""
    return jsonify(_get_context_data(current_user.id))


@ai_bp.route('/learner-profile', methods=['GET'])
@token_required
def get_learner_profile(current_user: User):
    target_date = request.args.get('date') or None
    try:
        profile = build_learner_profile(current_user.id, target_date)
    except ValueError:
        return jsonify({'error': 'date must be YYYY-MM-DD'}), 400
    return jsonify(profile)


# ── POST /api/ai/ask ──────────────────────────────────────────────────────────

SYSTEM_PROMPT = """你是一个 IELTS 英语词汇学习规划助手，名叫"雅思小助手"。请用中文回复用户。

你具备以下能力：
1. 分析用户的学习数据（进度、准确率、错词分布、当前学习状态、历史练习记录）
2. 给出学习计划建议（每日学习量、复习节奏），提供可操作的选项让用户选择
3. 激励用户保持学习习惯，结合用户目标和进步趋势给出针对性反馈
4. 解释英文单词的用法，通过网络搜索获取权威例句
5. 记住用户的目标、习惯、偏好，在未来对话中持续引用

## 工具使用指南

### remember_user_note — 持久化用户信息
当对话中出现以下信息时，**主动调用** 将其持久化（无需问用户）：
- 考试目标（如"目标7分"、"6月考试"）
- 每日学习计划（如"每天学30分钟"）
- 学习偏好、薄弱点、重要成就

### get_wrong_words — 获取错词列表
当用户问"我哪些词错得多"、"帮我复习错词"、"我的薄弱词汇"时调用。
参数：limit（数量，默认100）

### get_chapter_words — 获取章节单词
当用户问"第X章有哪些词"、"帮我看看这章内容"、"制定某章学习计划"时调用。
参数：book_id（词书ID）、chapter_id（章节号，整数）

### get_book_chapters — 获取词书章节结构
当用户问"这本书有几章"、"我完成了哪些章节"、"制定全书学习计划"时调用。
参数：book_id（词书ID）

**book_id 对照表：**
- 雅思听力高频词汇 → ielts_listening_premium
- 雅思阅读高频词汇 → ielts_reading_premium
- 雅思综合词汇5000+ → ielts_comprehensive
- 雅思终极词汇库 → ielts_ultimate
- AWL学术词汇表 → awl_academic

## 上下文优先级（从高到低）
1. 【AI记忆】— 跨会话持久的用户目标和 AI 笔记（最重要，始终优先引用）
2. 【历史对话摘要】— 压缩的旧会话上下文
3. 【最近练习记录】— 实际练习行为数据
4. 【当前学习状态】— 当前正在做什么
5. 【用户学习数据摘要】— 整体统计数字

## 最重要的原则：优先使用用户的真实数据
- 引用【AI记忆】中的内容时，要自然融入回复（"我记得你说过目标是7分…"）
- 如果用户问你记住了哪些单词，要明确说出具体单词名称，而不是泛泛而谈
- 如果用户在学习过程中问你当前单词的例句，先用 web_search 搜索真实例句
- 绝对不要在用户询问个人学习情况时给出通用词汇表

## 当用户没有历史数据时（totalLearned=0 或 [当前学习状态] 为空）
- 说明用户刚开始，先询问他们的目标：每天多少时间、目标分数等
- 获取到目标后立即用 remember_user_note 记录
- 不要给通用词汇表，而是制定第一阶段学习计划，提供选项让用户选择

## 回复格式规范

### 普通回复
直接用中文回复，内容清晰有条理。

### 建议型回复（需要用户确认）
在回复末尾用以下格式提供选项：
[options]
A. 选项A描述
B. 选项B描述
[/options]

示例（用户问今日计划）：
"根据你的数据，你今日可以学习50个新词，重点复习听力场景词汇。你想："
[options]
A. 好的，开始学习
B. 调整一下数量
C. 换个复习方向
[/options]

### 选项处理规则
- 用户可能只回复 "A" 或 "B" 等，识别并继续执行
- 回复选项时选项要有实际意义，每个选项要有明确的差异化

## 重要原则
- 如果看到【相关历史问答】，说明用户在同一主题反复卡住。要明确承认这一点，换一种解释方式，并主动追问是否需要更深入辨析、例句或小测。
- 不要编造例句，尽量通过网络搜索获取真实、地道的例句
- 建议要具体可执行（具体词数、时间安排）
- 语言要友好鼓励，不要过于严肃
- 如果用户还没有学习数据，鼓励他们开始学习
"""


def _build_context_msg(ctx: dict) -> str:
    """Build a readable context string from learning context dict."""
    parts = []
    dimension_labels = {
        'listening': '听音辨义',
        'meaning': '词义辨析',
        'dictation': '拼写默写',
    }

    # Book / chapter info
    if ctx.get('currentChapterTitle'):
        parts.append(f"当前章节：{ctx['currentChapterTitle']}")
    elif ctx.get('currentChapter'):
        parts.append(f"当前章节 ID：{ctx['currentChapter']}")
    if ctx.get('currentBook'):
        parts.append(f"当前词书 ID：{ctx['currentBook']}")

    if ctx.get('practiceMode'):
        parts.append(f"练习模式：{ctx['practiceMode']}")
    if ctx.get('mode'):
        parts.append(f"学习类型：{ctx['mode']}")

    # Session progress
    session_progress = ctx.get('sessionProgress')
    total_words = ctx.get('totalWords')
    words_completed = ctx.get('wordsCompleted')
    session_completed = ctx.get('sessionCompleted')

    if session_completed:
        parts.append(f"本轮练习：已完成全部 {total_words} 个单词")
        if words_completed is not None:
            parts.append(f"本轮答题数：{words_completed} 个")
    elif session_progress is not None:
        if total_words:
            parts.append(f"本次进度：{session_progress} / {total_words} 个词")
        else:
            parts.append(f"本次进度：{session_progress} 个词")
        if words_completed is not None:
            parts.append(f"本次已答题：{words_completed} 个")

    if ctx.get('sessionAccuracy') is not None:
        parts.append(f"本次准确率：{ctx['sessionAccuracy']}%")

    # Current word being studied (only when mid-session)
    if ctx.get('currentWord') and not session_completed:
        parts.append(f"当前单词：{ctx['currentWord']}")
        if ctx.get('currentPhonetic'):
            parts.append(f"  音标：{ctx['currentPhonetic']}")
        if ctx.get('currentPos'):
            parts.append(f"  词性：{ctx['currentPos']}")
        if ctx.get('currentDefinition'):
            parts.append(f"  释义：{ctx['currentDefinition']}")

    current_focus_dimension = ctx.get('currentFocusDimension')
    if current_focus_dimension:
        parts.append(
            f"当前训练焦点：{dimension_labels.get(current_focus_dimension, current_focus_dimension)}"
        )

    weak_dimension_order = ctx.get('weakDimensionOrder')
    if isinstance(weak_dimension_order, list) and weak_dimension_order:
        labels = [
            dimension_labels.get(str(item), str(item))
            for item in weak_dimension_order[:3]
            if item
        ]
        if labels:
            parts.append(f"当前薄弱维度：{'、'.join(labels)}")
    elif ctx.get('weakestDimension'):
        weakest_dimension = ctx.get('weakestDimension')
        parts.append(
            f"当前最弱维度：{dimension_labels.get(weakest_dimension, weakest_dimension)}"
        )

    weak_focus_words = ctx.get('weakFocusWords')
    if isinstance(weak_focus_words, list) and weak_focus_words:
        parts.append(f"当前重点薄弱词：{'、'.join(str(item) for item in weak_focus_words[:5])}")

    recent_wrong_words = ctx.get('recentWrongWords')
    if isinstance(recent_wrong_words, list) and recent_wrong_words:
        parts.append(f"近期易错词：{'、'.join(str(item) for item in recent_wrong_words[:5])}")

    trap_strategy = ctx.get('trapStrategy')
    if trap_strategy:
        parts.append(f"当前出题策略：{trap_strategy}")

    # Local historical summary (from localStorage)
    local = ctx.get('localHistory')
    if local and isinstance(local, dict):
        completed = local.get('chaptersCompleted', 0)
        attempted = local.get('chaptersAttempted', 0)
        accuracy = local.get('overallAccuracy', 0)
        correct = local.get('totalCorrect', 0)
        wrong = local.get('totalWrong', 0)
        if attempted > 0:
            parts.append(
                f"历史记录（本地）：已尝试 {attempted} 个章节，完成 {completed} 个，"
                f"累计答题 {correct + wrong} 次，准确率 {accuracy}%"
            )

    # Per-book breakdown from localStorage (richer than aggregate localHistory)
    local_book = ctx.get('localBookProgress')
    if local_book and isinstance(local_book, dict):
        from routes.books import VOCAB_BOOKS
        book_title_map = {b['id']: b['title'] for b in VOCAB_BOOKS}
        book_word_count_map = {b['id']: b.get('word_count', 0) for b in VOCAB_BOOKS}
        parts.append("本地各词书进度：")
        for book_id, stats in local_book.items():
            title = book_title_map.get(book_id, book_id)
            word_count = book_word_count_map.get(book_id, 0)
            ch_done = stats.get('chaptersCompleted', 0)
            ch_tried = stats.get('chaptersAttempted', 0)
            correct = stats.get('correct', 0)
            wrong = stats.get('wrong', 0)
            words_learned = stats.get('wordsLearned', 0)
            total = correct + wrong
            acc = round(correct / total * 100) if total > 0 else 0
            wc_str = f"（共{word_count}词）" if word_count else ""
            parts.append(
                f"  - {title}{wc_str}：已完成{ch_done}/{ch_tried}章，"
                f"已答{words_learned}词，正确率{acc}%"
            )

    return '\n'.join(parts) if parts else '暂无'


def _strip_options(text: str) -> str:
    """Remove [options]...[/options] blocks from text."""
    import re
    return re.sub(r'\[options\][\s\S]*?\[/options\]\s*', '', text).strip()


def _parse_options(text: str) -> list[str] | None:
    """Extract [options] blocks from text. Returns list of options or None."""
    import re
    pattern = r'\[options\]\s*([\s\S]*?)\s*\[/options\]'
    matches = re.findall(pattern, text)
    if not matches:
        return None
    # Extract individual lines
    options = []
    for block in matches:
        for line in block.strip().split('\n'):
            line = line.strip()
            if line and re.match(r'^[A-Z]\.', line):
                options.append(line)
    return options if options else None


_QUERY_STOPWORDS = {
    'the', 'and', 'for', 'with', 'that', 'this', 'have', 'what', 'when', 'where',
    'which', 'from', 'into', 'your', 'about', 'please', 'could', 'would', 'should',
    'kind',  # kept via currentWord / phrase overlap when relevant
}


def _extract_query_tokens(text: str) -> set[str]:
    english = {
        token.lower()
        for token in re.findall(r"[A-Za-z][A-Za-z'-]{1,}", text or '')
        if token.lower() not in _QUERY_STOPWORDS
    }
    chinese = {
        chunk
        for chunk in re.findall(r'[\u4e00-\u9fff]{2,}', text or '')
        if len(chunk.strip()) >= 2
    }
    return english | chinese


def _normalize_question_signature(text: str) -> str:
    lowered = (text or '').lower()
    lowered = re.sub(r'[^a-z0-9\u4e00-\u9fff]+', ' ', lowered)
    return re.sub(r'\s+', ' ', lowered).strip()


def _collect_related_learning_notes(
    user_id: int,
    user_message: str,
    frontend_context: dict | None = None,
    limit: int = 3,
) -> dict | None:
    query_tokens = _extract_query_tokens(user_message)
    normalized_message = _normalize_question_signature(user_message)
    current_word = ((frontend_context or {}).get('currentWord') or '').strip().lower()

    recent_notes = (
        UserLearningNote.query
        .filter_by(user_id=user_id)
        .order_by(UserLearningNote.created_at.desc())
        .limit(80)
        .all()
    )
    if not recent_notes:
        return None

    topic_matches: list[dict] = []
    memory_topics = build_memory_topics(
        recent_notes,
        limit=12,
        include_singletons=True,
        related_note_limit=max(limit + 2, 4),
    )
    for topic in memory_topics:
        related_notes = topic.get('related_notes') or []
        topic_text = ' '.join([
            str(topic.get('title') or ''),
            ' '.join(str(item.get('question') or '') for item in related_notes),
        ]).strip()
        topic_signature = _normalize_question_signature(topic_text)
        topic_tokens = _extract_query_tokens(topic_text)
        overlap = query_tokens & topic_tokens
        topic_word = str(topic.get('word_context') or '').strip().lower()

        score = len(overlap) * 2
        if current_word and topic_word == current_word:
            score += 4
        if topic_signature and normalized_message and (
            topic_signature in normalized_message or normalized_message in topic_signature
        ):
            score += 4
        if current_word and current_word in topic_signature:
            score += 1

        if score < 3:
            continue

        items: list[dict] = []
        for item in related_notes[:limit]:
            created_at = item.get('created_at')
            created_at_dt = None
            if isinstance(created_at, datetime):
                created_at_dt = created_at
            elif isinstance(created_at, str) and created_at:
                try:
                    created_at_dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                except ValueError:
                    created_at_dt = None

            items.append({
                'question': item.get('question') or '',
                'answer': item.get('answer') or '',
                'word_context': item.get('word_context') or '',
                'created_at': created_at_dt or created_at,
            })

        latest_at = topic.get('latest_at')
        latest_at_dt = None
        if isinstance(latest_at, datetime):
            latest_at_dt = latest_at
        elif isinstance(latest_at, str) and latest_at:
            try:
                latest_at_dt = datetime.fromisoformat(latest_at.replace('Z', '+00:00'))
            except ValueError:
                latest_at_dt = None

        topic_matches.append({
            'score': score,
            'repeat_count': int(topic.get('count') or len(items)),
            'items': items,
            'follow_up_hint': topic.get('follow_up_hint') or '',
            'latest_at': latest_at_dt or datetime.min,
        })

    if not topic_matches:
        return None

    topic_matches.sort(
        key=lambda item: (item['score'], item['repeat_count'], item['latest_at']),
        reverse=True,
    )
    best = topic_matches[0]
    return {
        'repeat_count': best['repeat_count'],
        'items': best['items'][:limit],
        'follow_up_hint': best['follow_up_hint'],
    }


def _build_related_notes_msg(related_notes: dict | None) -> str | None:
    if not related_notes:
        return None

    repeat_count = int(related_notes.get('repeat_count') or 0)
    items = related_notes.get('items') or []
    follow_up_hint = str(related_notes.get('follow_up_hint') or '').strip()
    if not items:
        return None

    lines = ['[相关历史问答]']
    if repeat_count >= 2:
        lines.append(f"这个主题用户已重复询问 {repeat_count} 次，说明这里可能还没有真正吃透。")
    else:
        lines.append("下面是和当前问题最相关的历史问答，请优先利用。")

    for index, item in enumerate(items, start=1):
        created_at = item.get('created_at')
        date_text = created_at.strftime('%Y-%m-%d') if isinstance(created_at, datetime) else '最近'
        question = str(item.get('question') or '').strip()[:180]
        answer = str(item.get('answer') or '').strip().replace('\n', ' ')[:220]
        word_context = str(item.get('word_context') or '').strip()
        suffix = f"（关联单词：{word_context}）" if word_context else ''
        lines.append(f"{index}. {date_text} | 问：{question}{suffix}")
        lines.append(f"   答：{answer}")

    if repeat_count >= 2:
        lines.append("回答要求：先承认用户之前问过这个点，换一种解释角度，并主动询问是否需要进一步辨析、例句或小测。")

    if follow_up_hint:
        lines.append(f"[Follow-up hint] {follow_up_hint}")

    return '\n'.join(lines)


# ── Tool input schemas (whitelist validation) ─────────────────────────────────
# Maps tool_name → {param: (type, max_len_or_None)}
_TOOL_INPUT_SCHEMA: dict[str, dict[str, tuple]] = {
    "web_search": {
        "query": (str, 500),
    },
    "remember_user_note": {
        "note":     (str, 500),
        "category": (str, 50),
    },
    "get_wrong_words": {
        "limit": (int, None),
    },
    "get_chapter_words": {
        "book_id": (str, 100),
        "chapter_id": (int, None),
    },
    "get_book_chapters": {
        "book_id": (str, 100),
    },
}

_VALID_CATEGORIES = {'goal', 'habit', 'weakness', 'preference', 'achievement', 'other'}


def _validate_tool_input(tool_name: str, tool_input: dict) -> dict | None:
    """
    Validate and sanitize tool inputs against the whitelist schema.
    Returns a cleaned dict, or None if validation fails.
    """
    schema = _TOOL_INPUT_SCHEMA.get(tool_name)
    if schema is None:
        return None   # Unknown tool — reject

    cleaned = {}
    for param, (expected_type, max_len) in schema.items():
        val = tool_input.get(param)
        if val is None:
            continue
        if not isinstance(val, expected_type):
            return None
        if max_len and isinstance(val, str):
            val = val[:max_len]
        cleaned[param] = val

    # Extra whitelist check for category
    if tool_name == "remember_user_note":
        cat = cleaned.get("category", "other")
        if cat not in _VALID_CATEGORIES:
            cleaned["category"] = "other"

    return cleaned


def _chat_with_tools(
    messages: list[dict],
    tools: list | None = None,
    max_iterations: int = 5,
    extra_handlers: dict | None = None,
) -> dict:
    """
    Chat with MiniMax, automatically handling tool_use blocks.
    Appends assistant responses and tool results to messages in-place.
    Returns the final text response.

    extra_handlers: optional dict of {tool_name: callable} that extends/overrides
    TOOL_HANDLERS for this call (used to inject per-request handlers, e.g. memory writes).
    """
    handlers = {**TOOL_HANDLERS, **(extra_handlers or {})}
    for i in range(max_iterations):
        response = chat(messages, tools=tools, max_tokens=4096)

        if response.get("type") == "tool_call":
            tool_name = response.get("tool")
            raw_input = response.get("input", {})
            tool_call_id = response.get("tool_call_id", f"call_{i}")
            handler = handlers.get(tool_name)

            # Validate + sanitize tool inputs before execution
            tool_input = _validate_tool_input(tool_name, raw_input) if isinstance(raw_input, dict) else None

            if handler and tool_input is not None:
                try:
                    result = handler(**tool_input)
                except Exception as e:
                    result = f"Tool error: {e}"

                # Append assistant message with tool_use reference
                messages.append({
                    "role": "assistant",
                    "content": [{
                        "type": "tool_use",
                        "id": tool_call_id,
                        "name": tool_name,
                        "input": tool_input
                    }]
                })
                # Append tool result
                messages.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": tool_call_id,
                        "content": result
                    }]
                })
            elif handler and tool_input is None:
                # Tool input failed validation — log and continue
                import logging as _log
                _log.warning(f"[AI] Tool '{tool_name}' input validation failed: {raw_input!r}")
                messages.append({
                    "role": "assistant",
                    "content": f"[Tool '{tool_name}' input validation failed]"
                })
            else:
                messages.append({
                    "role": "assistant",
                    "content": f"[Tool '{tool_name}' not available]"
                })
        else:
            return response

    # Max iterations reached
    return {"type": "text", "text": "[对话轮次过多，已停止]"}


GREET_SYSTEM_PROMPT = """你是一个 IELTS 英语词汇学习规划助手，名叫"雅思小助手"。请用中文回复用户。

你的任务是生成一条个性化的问候语，让用户感到被关注和激励。

## 问候规则
- 如果用户有历史学习数据（totalLearned > 0），回顾他们的进度并鼓励继续
- 如果用户正在学习中（有 [当前学习状态]），提及当前进度
- 如果用户是新用户（totalLearned=0），热情欢迎，引导开始学习
- 问候语要简洁（3-5句话），不要过长
- 可以提供 2-3 个选项让用户快速选择接下来要做什么

## 回复格式
直接输出问候内容，可在末尾加选项：
[options]
A. 选项A
B. 选项B
[/options]
"""


GREET_SYSTEM_PROMPT_V2 = """你是一个 IELTS 英语词汇学习规划助手，名叫“雅思小助手”。请用中文回复用户。

你的任务是生成一条个性化的开场问候，让用户一打开就感到“这个助手记得我、理解我现在卡在哪”。

## 问候目标
- 优先利用学习画像、重复困惑主题、薄弱模式、重点突破词来组织问候。
- 如果用户近期反复卡在某个辨析点，要主动点出来，并说明你可以换一种讲法继续讲透。
- 如果用户今天有明确的训练焦点或弱项，要顺着这个焦点自然开场，不要只说泛泛的“继续加油”。
- 如果是新用户或几乎没有学习数据，再使用简单欢迎语。

## 输出规则
- 问候语保持 3-5 句，简洁、自然、像真人老师开场，不要写成模板化播报。
- 默认输出自然问候，不要默认输出选项，也不要把问候强行写成选择题。
- 只有当用户下一步动作非常明确时，才在末尾附 1-2 个简短选项。
- 如果提供选项，选项必须紧扣用户画像，而不是通用话术。

## 允许的选项格式
[options]
A. 选项A
B. 选项B
[/options]
"""

def _build_learning_context_msg(ctx_data: dict, frontend_context: dict) -> str:
    """Build a combined context message from server data + frontend state."""
    from datetime import datetime
    parts = []

    # ── Current date (so AI can make accurate plans) ──────────────────────────
    import calendar
    weekday_zh = ['一', '二', '三', '四', '五', '六', '日']
    now = datetime.now()
    days_in_month = calendar.monthrange(now.year, now.month)[1]
    days_left = days_in_month - now.day
    parts.append(
        f"【今日日期】{now.strftime('%Y年%m月%d日')}，"
        f"星期{weekday_zh[now.weekday()]}，本月还剩{days_left}天"
    )

    # ── Persistent AI memory (goals, notes, compressed history) ──────────────
    memory = ctx_data.get('memory', {})
    goals = memory.get('goals', {})
    ai_notes = memory.get('ai_notes', [])
    conv_summary = memory.get('conversation_summary', '')

    if goals or ai_notes or conv_summary:
        parts.append("【AI记忆（跨会话持久）】")
        if goals:
            goal_parts = []
            if goals.get('target_band'):
                goal_parts.append(f"目标分数：{goals['target_band']}")
            if goals.get('exam_date'):
                goal_parts.append(f"考试日期：{goals['exam_date']}")
            if goals.get('daily_minutes'):
                goal_parts.append(f"每日学习：{goals['daily_minutes']}分钟")
            if goals.get('focus'):
                goal_parts.append(f"重点方向：{goals['focus']}")
            if goal_parts:
                parts.append("  用户目标：" + "，".join(goal_parts))
        if ai_notes:
            cat_zh = {'goal': '目标', 'habit': '习惯', 'weakness': '薄弱', 'preference': '偏好', 'achievement': '成就', 'other': '其他'}
            for n in ai_notes[-10:]:  # last 10 notes
                cat = cat_zh.get(n.get('category', 'other'), n.get('category', ''))
                parts.append(f"  [{cat}] {n.get('note', '')}（{n.get('created_at', '')}）")
        if conv_summary:
            parts.append(f"\n【历史对话摘要】\n{conv_summary}")

    # Server-side learning summary
    total_learned = ctx_data.get('totalLearned', 0)
    total_correct = ctx_data.get('totalCorrect', 0)
    total_wrong = ctx_data.get('totalWrong', 0)
    accuracy = ctx_data.get('accuracyRate', 0)
    trend = ctx_data.get('recentTrend', 'new')
    books = ctx_data.get('books', [])
    wrong_words = ctx_data.get('wrongWords', [])
    recent_sessions = ctx_data.get('recentSessions', [])
    chapter_stats = ctx_data.get('chapterSessionStats', [])
    learner_profile = ctx_data.get('learnerProfile', {})

    trend_zh = {'improving': '上升', 'declining': '下滑', 'stable': '平稳', 'new': '刚开始'}.get(trend, trend)

    parts.append(
        f"【用户学习数据摘要】\n"
        f"总学习词数：{total_learned}\n"
        f"总正确数：{total_correct}  总错误数：{total_wrong}\n"
        f"整体准确率：{accuracy}%\n"
        f"近期趋势：{trend_zh}\n"
        f"正在学习的词书：{len(books)} 本"
    )
    for b in books:
        word_count = b.get('wordCount', 0)
        correct = b.get('correctCount', 0)
        wc_str = f"共{word_count}词、" if word_count else ""
        parts.append(
            f"  - {b.get('title', b.get('id'))} "
            f"({wc_str}已答对{correct}词、准确率{b.get('accuracy', 0)}%、错词数{b.get('wrongCount', 0)})"
        )

    # ── Recent sessions (最近练习记录) ────────────────────────────────────────
    if recent_sessions:
        parts.append("\n【最近练习记录（最新10条）】")
        mode_zh = {
            'smart': '智能', 'listening': '听音选义', 'meaning': '看词选义',
            'dictation': '听写', 'radio': '随身听', 'quickmemory': '速记',
        }
        for s in recent_sessions:
            date_str = (s.get('started_at') or '')[:10]
            mode_label = mode_zh.get(s.get('mode', ''), s.get('mode', '未知'))
            chapter_label = f"第{s.get('chapter_id', '?')}章" if s.get('chapter_id') else '全书'
            book_label = s.get('book_title') or s.get('book_id') or '?'
            dur = s.get('duration_seconds', 0) or 0
            dur_str = f"{dur // 60}分{dur % 60}秒" if dur >= 60 else f"{dur}秒"
            parts.append(
                f"  {date_str} | {book_label} {chapter_label} | {mode_label} | "
                f"{s.get('words_studied', 0)}词 | 正确率{s.get('accuracy', 0)}% | 用时{dur_str}"
            )
    else:
        parts.append("\n【最近练习记录】暂无")

    # ── Per-chapter repeated practice stats ───────────────────────────────────
    repeated = [c for c in chapter_stats if c.get('session_count', 0) >= 2]
    if repeated:
        # Sort by session count desc, show top 5
        repeated.sort(key=lambda c: c.get('session_count', 0), reverse=True)
        parts.append("\n【多次练习章节（练了2次以上的）】")
        for c in repeated[:5]:
            acc_list = c.get('accuracies', [])
            acc_str = ' → '.join(f"{a}%" for a in acc_list[-5:])  # last 5 sessions
            modes_str = '、'.join(c.get('modes', []))
            parts.append(
                f"  {c.get('book_title', c.get('book_id', '?'))} 第{c.get('chapter_id', '?')}章："
                f"共练 {c.get('session_count')} 次，"
                f"平均正确率 {c.get('avg_accuracy')}%，"
                f"趋势 {c.get('trend', '—')}，"
                f"各次正确率 [{acc_str}]，"
                f"使用模式：{modes_str}"
            )

    if wrong_words:
        words_list = '、'.join([w['word'] for w in wrong_words[:20]])
        parts.append(f"\n错词列表（最近50条）：{words_list}")
    else:
        parts.append("\n错词列表：暂无")

    if learner_profile and isinstance(learner_profile, dict):
        summary = learner_profile.get('summary') or {}
        dimensions = learner_profile.get('dimensions') or []
        focus_words = learner_profile.get('focus_words') or []
        repeated_topics = learner_profile.get('repeated_topics') or []
        next_actions = learner_profile.get('next_actions') or []

        parts.append("\n[统一学习画像]")
        weakest_mode_label = summary.get('weakest_mode_label') or summary.get('weakest_mode')
        weakest_mode_accuracy = summary.get('weakest_mode_accuracy')
        if weakest_mode_label:
            suffix = f"（准确率 {weakest_mode_accuracy}%）" if weakest_mode_accuracy is not None else ''
            parts.append(f"当前最弱模式：{weakest_mode_label}{suffix}")
        if dimensions:
            dimension_text = '、'.join(
                f"{item.get('label', item.get('dimension'))} {item.get('accuracy')}%"
                for item in dimensions[:3]
            )
            parts.append(f"薄弱维度排序：{dimension_text}")
        if focus_words:
            focus_text = '、'.join(item.get('word', '') for item in focus_words[:5] if item.get('word'))
            if focus_text:
                parts.append(f"重点突破词：{focus_text}")
        if repeated_topics:
            parts.append("重复困惑主题：")
            for topic in repeated_topics[:3]:
                parts.append(f"  - {topic.get('title', '')}（重复 {topic.get('count', 0)} 次）")
        if next_actions:
            parts.append("建议动作：")
            for action in next_actions[:3]:
                parts.append(f"  - {action}")

    # Frontend session context
    if frontend_context:
        ctx_str = _build_context_msg(frontend_context)
        if ctx_str and ctx_str != '暂无':
            parts.append(f"\n[当前学习状态]\n{ctx_str}")

    return '\n'.join(parts)


def _build_greet_fallback(current_user: User, ctx_data: dict | None = None) -> str:
    """Return a stable local greeting when the AI provider is unavailable."""
    name = (getattr(current_user, 'username', None) or '同学').strip() or '同学'
    ctx_data = ctx_data or {}

    total_learned = int(ctx_data.get('totalLearned') or 0)
    accuracy_rate = ctx_data.get('accuracyRate')
    wrong_words = ctx_data.get('wrongWords') or []
    recent_sessions = ctx_data.get('recentSessions') or []
    learner_profile = ctx_data.get('learnerProfile') or {}
    dimensions = learner_profile.get('dimensions') or []
    focus_words = learner_profile.get('focus_words') or []
    repeated_topics = learner_profile.get('repeated_topics') or []
    next_actions = learner_profile.get('next_actions') or []

    if total_learned <= 0 and not recent_sessions and not repeated_topics and not focus_words and not dimensions:
        return f"你好，{name}！我是雅思小助手。你可以告诉我今天想学哪本词书，或者直接开始一章练习。"

    parts = [f"你好，{name}！我是雅思小助手。"]

    if repeated_topics:
        topic = repeated_topics[0] or {}
        topic_title = str(topic.get('title') or '').strip()
        topic_count = int(topic.get('count') or 0)
        if topic_title:
            repeat_text = f"这个点你已经反复问过 {topic_count} 次" if topic_count > 1 else "这个点你最近又问到了"
            parts.append(f"我注意到你最近在“{topic_title}”上有些卡住，{repeat_text}，这次我可以换个更容易抓住差别的讲法。")
    elif focus_words:
        focus_text = '、'.join(item.get('word', '') for item in focus_words[:3] if item.get('word'))
        if focus_text:
            parts.append(f"你这阶段的重点突破词主要集中在 {focus_text}，我可以顺着这些词继续帮你拆开辨析。")

    if total_learned > 0:
        summary = f"你已经累计学习了 {total_learned} 个词"
        if isinstance(accuracy_rate, (int, float)):
            summary += f"，整体正确率约 {int(accuracy_rate)}%"
        parts.append(summary + "。")

    if dimensions:
        dimension = dimensions[0] or {}
        label = str(dimension.get('label') or dimension.get('dimension') or '').strip()
        accuracy = dimension.get('accuracy')
        if label:
            accuracy_suffix = f"，目前准确率大约 {int(accuracy)}%" if isinstance(accuracy, (int, float)) else ''
            parts.append(f"当前最值得优先补的是“{label}”{accuracy_suffix}。")
    elif wrong_words:
        focus_text = '、'.join(w.get('word', '') for w in wrong_words[:3] if w.get('word'))
        if focus_text:
            parts.append(f"近期可以优先复习：{focus_text}。")

    if next_actions:
        first_action = str(next_actions[0]).strip()
        if first_action:
            parts.append(f"如果你愿意，我们可以先从“{first_action}”开始。")
    elif recent_sessions:
        latest = recent_sessions[0]
        book_title = latest.get('book_title') or latest.get('book_id') or '当前词书'
        chapter_id = latest.get('chapter_id')
        chapter_label = f"第{chapter_id}章" if chapter_id else '当前章节'
        parts.append(f"如果你愿意，我可以继续围绕 {book_title} {chapter_label} 帮你安排复习。")
    else:
        parts.append("如果你愿意，我可以根据你最近的学习情况帮你安排下一步复习。")

    return ''.join(parts)


@ai_bp.route('/greet', methods=['POST'])
@token_required
def greet(current_user: User):
    """
    Personalized greeting — called when user opens the AI chat panel.
    Returns a greeting based on the user's real learning progress.
    """
    body = request.get_json(silent=True) or {}
    frontend_context = body.get('context') or {}

    messages = [{"role": "system", "content": GREET_SYSTEM_PROMPT_V2}]

    ctx_data = {}
    try:
        ctx_data = _get_context_data(current_user.id)
        context_msg = _build_learning_context_msg(ctx_data, frontend_context)
        messages.append({
            "role": "user",
            "content": (
                "补充要求：如果画像已经显示明显弱点、重复困惑主题或重点突破词，优先围绕这些点自然开场。"
                "不要默认输出选项；只有当下一步动作非常明确时，才补 1-2 个简短选项。"
            ),
        })
        messages.append({"role": "user", "content": f"[学习数据]\n{context_msg}\n\n请根据以上数据，生成一条个性化的问候。"})
    except Exception as e:
        import logging
        logging.warning(f"[AI] greet context load failed for user={current_user.id}: {e}")
        messages.append({
            "role": "user",
            "content": "补充要求：默认自然开场，不要默认输出选项。",
        })
        messages.append({"role": "user", "content": "请生成一条欢迎问候语，用户可能刚开始学习。"})

    try:
        response = _chat_with_tools(messages, tools=None)
        final_text = response.get("text", str(response))
        options = _parse_options(final_text) or []
        clean_reply = _strip_options(final_text).strip()
        # Save greeting as the opening assistant turn so /ask can reference it
        _save_turn(current_user.id, '[用户打开了AI助手]', clean_reply)
        return jsonify({'reply': clean_reply, 'options': options})
    except Exception as e:
        import logging
        logging.warning(f"[AI] greet failed for user={current_user.id}: {e}")
        fallback_reply = _build_greet_fallback(current_user, ctx_data)
        _save_turn(current_user.id, '[用户打开了AI助手]', fallback_reply)
        return jsonify({'reply': fallback_reply, 'options': []}), 200


# ── Feature APIs (PRD Phase 1-4) ─────────────────────────────────────────────

@ai_bp.route('/correct-text', methods=['POST'])
@token_required
def correct_text_api(current_user: User):
    body = request.get_json() or {}
    text_in = (body.get('text') or '').strip()
    if not text_in:
        return jsonify({
            'is_valid_english': False,
            'message': '请输入英文句子（建议 1-50 词）。',
        }), 200
    if len(text_in.split()) > 80:
        return jsonify({'error': '句子过长，请控制在 80 词内'}), 400

    result = correct_text(text_in)
    _track_metric(current_user.id, 'writing_correction_used', {'length': len(text_in.split())})
    return jsonify(result), 200


@ai_bp.route('/correction-feedback', methods=['POST'])
@token_required
def correction_feedback(current_user: User):
    body = request.get_json() or {}
    adopted = bool(body.get('adopted'))
    _track_metric(current_user.id, 'writing_correction_adoption', {'adopted': adopted})
    return jsonify({'ok': True}), 200


@ai_bp.route('/ielts-example', methods=['GET'])
@token_required
def ielts_example(current_user: User):
    word = (request.args.get('word') or '').strip().lower()
    if not word:
        return jsonify({'error': 'word is required'}), 400

    corpus = _load_json_data('ielts-reading-corpus.json', {})
    topic_map = _load_json_data('ielts-topics.json', {})
    items = corpus.get(word, [])
    if items:
        _track_metric(current_user.id, 'ielts_example_hit', {'word': word, 'count': len(items)})
        return jsonify({'word': word, 'source': 'ielts-corpus', 'examples': items[:5]}), 200

    # 降级：web_search
    summary = web_search(f"{word} IELTS reading sentence examples")
    fallback = [{
        'sentence': summary.split('\n')[0][:220],
        'source': 'web_search',
        'topic': topic_map.get(word, 'general'),
        'is_real_exam': False,
    }]
    _track_metric(current_user.id, 'ielts_example_fallback', {'word': word})
    return jsonify({'word': word, 'source': 'fallback', 'examples': fallback}), 200


@ai_bp.route('/synonyms-diff', methods=['POST'])
@token_required
def synonyms_diff(current_user: User):
    body = request.get_json() or {}
    a = (body.get('a') or '').strip()
    b = (body.get('b') or '').strip()
    if not a or not b:
        return jsonify({'error': 'a and b are required'}), 400
    result = differentiate_synonyms(a, b)
    _track_metric(current_user.id, 'synonyms_diff_used', {'pair': f'{a}-{b}'})
    return jsonify(result), 200


@ai_bp.route('/word-family', methods=['GET'])
@token_required
def word_family(current_user: User):
    word = (request.args.get('word') or '').strip().lower()
    if not word:
        return jsonify({'error': 'word is required'}), 400
    db_json = _load_json_data('word-families.json', {})
    data = db_json.get(word)
    if not data:
        return jsonify({
            'word': word,
            'message': '暂未收录该词族，建议查询实义词（如 establish / analyze / regulate）。',
        }), 200
    _track_metric(current_user.id, 'word_family_used', {'word': word})
    return jsonify(data), 200


@ai_bp.route('/word-family/quiz', methods=['GET'])
@token_required
def word_family_quiz(current_user: User):
    word = (request.args.get('word') or '').strip().lower()
    db_json = _load_json_data('word-families.json', {})
    data = db_json.get(word, {})
    variants = data.get('variants', [])
    if len(variants) < 2:
        return jsonify({'error': 'not enough variants'}), 400
    picked = random.choice(variants)
    others = [v.get('word') for v in variants if v.get('word') and v.get('word') != picked.get('word')]
    return jsonify({
        'prompt': f"请说出与 {picked.get('word')} 同词族的另外两个词",
        'answer_candidates': others[:4],
        'analysis': f"{picked.get('word')} 属于 {word} 词族，注意词性转换。",
    }), 200


@ai_bp.route('/collocations/practice', methods=['GET'])
@token_required
def collocation_practice(current_user: User):
    topic = (request.args.get('topic') or 'general').strip().lower()
    mode = (request.args.get('mode') or 'mcq').strip().lower()
    count = min(max(int(request.args.get('count', 5)), 1), 20)
    pool = _load_json_data('ielts-collocations.json', [])
    filtered = [x for x in pool if x.get('topic', 'general') in (topic, 'general')] or pool
    random.shuffle(filtered)
    _track_metric(current_user.id, 'collocation_practice_used', {'topic': topic, 'mode': mode, 'count': count})
    return jsonify({'topic': topic, 'mode': mode, 'items': filtered[:count]}), 200


@ai_bp.route('/pronunciation-check', methods=['POST'])
@token_required
def pronunciation_check(current_user: User):
    body = request.get_json() or {}
    word = (body.get('word') or '').strip()
    transcript = (body.get('transcript') or '').strip()
    if not word:
        return jsonify({'error': 'word is required'}), 400
    # 规则兜底：后续可接 MiniMax 语音识别
    score = 85 if transcript.lower() == word.lower() else 65
    result = {
        'word': word,
        'score': score,
        'stress_feedback': '重音位置基本正确，建议再拉长重读音节。',
        'vowel_feedback': '元音饱满度中等，可再放慢语速。',
        'speed_feedback': '语速可接受，注意词尾清晰度。',
    }
    _track_metric(current_user.id, 'pronunciation_check_used', {'word': word, 'score': score})
    return jsonify(result), 200


@ai_bp.route('/speaking-simulate', methods=['POST'])
@token_required
def speaking_simulate(current_user: User):
    body = request.get_json() or {}
    part = int(body.get('part', 1))
    topic = (body.get('topic') or 'education').strip()
    qmap = {
        1: f"Part 1: Do you enjoy learning vocabulary about {topic}?",
        2: f"Part 2: Describe a time when {topic} vocabulary helped your IELTS performance.",
        3: f"Part 3: How can schools improve students' {topic} related lexical resources?",
    }
    _track_metric(current_user.id, 'speaking_simulation_used', {'part': part, 'topic': topic})
    return jsonify({
        'part': part,
        'topic': topic,
        'question': qmap.get(part, qmap[1]),
        'follow_ups': ['请给出一个具体例子。', '能否用更学术的表达重述？'],
    }), 200


@ai_bp.route('/review-plan', methods=['GET'])
@token_required
def review_plan(current_user: User):
    ctx = _get_context_data(current_user.id)
    wrong_count = len(ctx.get('wrongWords', []))
    accuracy = ctx.get('accuracyRate', 0)
    if accuracy >= 80:
        level = 'balanced'
        plan = ['新词 20 个', '复习 30 个', '错词回顾 10 分钟']
    else:
        level = 'recovery'
        plan = ['新词 10 个', '复习 40 个', '错词精练 20 分钟']
    _track_metric(current_user.id, 'adaptive_plan_generated', {'level': level})
    return jsonify({'level': level, 'wrong_words': wrong_count, 'plan': plan}), 200


@ai_bp.route('/vocab-assessment', methods=['GET'])
@token_required
def vocab_assessment(current_user: User):
    count = min(max(int(request.args.get('count', 20)), 5), 50)
    pool = _get_global_vocab_pool()
    random.shuffle(pool)
    questions = []
    for w in pool[:count]:
        questions.append({
            'word': w.get('word'),
            'definition': w.get('definition'),
            'pos': w.get('pos'),
        })
    _track_metric(current_user.id, 'vocab_assessment_generated', {'count': count})
    return jsonify({'count': len(questions), 'questions': questions}), 200


# ── Conversation history helpers ──────────────────────────────────────────────

_HISTORY_LIMIT = 20  # max past turns to include in context


def _load_history(user_id: int) -> list[dict]:
    """Load last N conversation turns from DB as LLM-ready message dicts."""
    rows = (
        UserConversationHistory.query
        .filter_by(user_id=user_id)
        .order_by(UserConversationHistory.created_at.desc())
        .limit(_HISTORY_LIMIT)
        .all()
    )
    # Reverse so oldest first
    return [{"role": r.role, "content": r.content} for r in reversed(rows)]


_HISTORY_PRUNE_DAYS = 90   # delete conversation records older than this


def _save_turn(user_id: int, user_message: str, assistant_reply: str):
    """Persist a user+assistant turn to DB, and prune records older than 90 days."""
    from datetime import timedelta
    import logging
    try:
        db.session.add(UserConversationHistory(
            user_id=user_id, role='user', content=user_message
        ))
        db.session.add(UserConversationHistory(
            user_id=user_id, role='assistant', content=assistant_reply
        ))
        # Prune old history rows (>90 days) to cap table growth
        cutoff = datetime.utcnow() - timedelta(days=_HISTORY_PRUNE_DAYS)
        UserConversationHistory.query.filter(
            UserConversationHistory.user_id == user_id,
            UserConversationHistory.created_at < cutoff,
        ).delete(synchronize_session=False)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logging.warning(f"[AI] Failed to save conversation turn: {e}")


# ── User memory helpers ───────────────────────────────────────────────────────

def _get_or_create_memory(user_id: int) -> 'UserMemory':
    """Return the UserMemory row for this user, creating it if absent.
    Uses INSERT OR IGNORE to avoid UNIQUE constraint races under concurrency."""
    from sqlalchemy.exc import IntegrityError
    mem = UserMemory.query.filter_by(user_id=user_id).first()
    if not mem:
        try:
            mem = UserMemory(user_id=user_id)
            db.session.add(mem)
            db.session.flush()
        except IntegrityError:
            # Another request created it concurrently — rollback and re-fetch
            db.session.rollback()
            mem = UserMemory.query.filter_by(user_id=user_id).first()
    return mem


def _load_memory(user_id: int) -> dict:
    """Return serialisable memory dict for context injection."""
    mem = UserMemory.query.filter_by(user_id=user_id).first()
    if not mem:
        return {}
    return {
        'goals': mem.get_goals(),
        'ai_notes': mem.get_ai_notes(),
        'conversation_summary': mem.conversation_summary or '',
    }


def _add_memory_note(user_id: int, note: str, category: str) -> str:
    """Append an AI-written note to UserMemory.ai_notes. Returns confirmation."""
    from datetime import datetime as _dt
    try:
        mem = _get_or_create_memory(user_id)
        notes = mem.get_ai_notes()
        # Avoid exact duplicates
        if not any(n.get('note') == note for n in notes):
            notes.append({
                'category': category,
                'note': note,
                'created_at': _dt.utcnow().strftime('%Y-%m-%d'),
            })
            # Keep last 30 notes to avoid unbounded growth
            mem.set_ai_notes(notes[-30:])
        db.session.commit()
        return f"已记录：[{category}] {note}"
    except Exception as e:
        db.session.rollback()
        import logging
        logging.warning(f"[AI] Failed to save memory note: {e}")
        return f"记录失败：{e}"


# Threshold: when total turns exceed this, compress the oldest chunk
_SUMMARIZE_THRESHOLD = 40   # total turns before triggering compression
_SUMMARIZE_CHUNK = 20       # how many old turns to compress each time


def _maybe_summarize_history(user_id: int):
    """If conversation history is long, compress old turns into UserMemory.conversation_summary."""
    total = UserConversationHistory.query.filter_by(user_id=user_id).count()
    mem = UserMemory.query.filter_by(user_id=user_id).first()
    already_summarized = mem.summary_turn_count if mem else 0

    unsummarized = total - already_summarized
    if unsummarized <= _SUMMARIZE_THRESHOLD:
        return  # Not enough new turns yet

    # Fetch the oldest un-summarized chunk
    old_rows = (
        UserConversationHistory.query
        .filter_by(user_id=user_id)
        .order_by(UserConversationHistory.created_at.asc())
        .offset(already_summarized)
        .limit(_SUMMARIZE_CHUNK)
        .all()
    )
    if not old_rows:
        return

    # Build a conversation snippet for the LLM to summarize
    snippet = '\n'.join(
        f"{'用户' if r.role == 'user' else 'AI'}：{r.content[:300]}"
        for r in old_rows
    )
    existing_summary = mem.conversation_summary if mem else ''

    summary_prompt = [
        {"role": "system", "content": (
            "你是一个摘要助手，请将以下对话压缩为一段简洁的中文摘要（100-200字），"
            "重点保留：用户的学习目标、偏好、困难、AI给出的重要建议和用户的关键反应。"
            "不要编造内容，只提炼对话中已有的信息。"
        )},
        {"role": "user", "content": (
            (f"【已有摘要】\n{existing_summary}\n\n" if existing_summary else '') +
            f"【新增对话（{len(old_rows)}条）】\n{snippet}\n\n"
            "请输出更新后的完整摘要："
        )},
    ]
    try:
        resp = chat(summary_prompt, max_tokens=400)
        new_summary = resp.get('text', '').strip()
        if new_summary:
            mem = _get_or_create_memory(user_id)
            mem.conversation_summary = new_summary
            mem.summary_turn_count = already_summarized + len(old_rows)
            db.session.commit()
    except Exception as e:
        import logging
        logging.warning(f"[AI] Summarization failed for user={user_id}: {e}")


# ── Per-request tool handlers (need user_id, built inside ask()) ──────────────

def _make_get_wrong_words(user_id: int):
    def handler(limit: int = 100, book_id: str | None = None) -> str:
        limit = min(int(limit), 300)
        q = UserWrongWord.query.filter_by(user_id=user_id)
        words = q.order_by(UserWrongWord.wrong_count.desc()).limit(limit).all()
        if not words:
            return "暂无错词记录。"
        prefix = ''
        if book_id:
            prefix = "当前错词记录暂不支持按词书过滤，以下返回全部错词。\n"
        lines = [f"{w.word}（{w.phonetic or ''}，{w.pos or ''}）{w.definition or ''}  错误{w.wrong_count}次" for w in words]
        return prefix + f"共{len(lines)}个错词：\n" + "\n".join(lines)
    return handler


def _make_get_chapter_words(user_id: int):
    def handler(book_id: str, chapter_id: int) -> str:
        from routes.books import load_book_vocabulary, VOCAB_BOOKS
        book = next((b for b in VOCAB_BOOKS if b['id'] == book_id), None)
        if not book:
            return f"找不到词书 '{book_id}'，请检查 book_id 是否正确。"
        vocab = load_book_vocabulary(book_id)
        if not vocab:
            return f"词书 '{book['title']}' 的单词数据加载失败。"
        chapter_words = [w for w in vocab if w.get('chapter_id') == chapter_id]
        if not chapter_words:
            return f"词书 '{book['title']}' 中找不到第{chapter_id}章，或该章无单词。"
        chapter_title = chapter_words[0].get('chapter_title', f'第{chapter_id}章')
        lines = [
            f"{w['word']}  {w.get('phonetic', '')}  [{w.get('pos', '')}]  {w.get('definition', '')}"
            for w in chapter_words
        ]
        return f"{book['title']} — {chapter_title}（共{len(lines)}词）：\n" + "\n".join(lines)
    return handler


def _make_get_book_chapters(user_id: int):
    def handler(book_id: str) -> str:
        from routes.books import load_book_chapters, VOCAB_BOOKS
        book = next((b for b in VOCAB_BOOKS if b['id'] == book_id), None)
        if not book:
            return f"找不到词书 '{book_id}'，请检查 book_id 是否正确。"
        structure = load_book_chapters(book_id)
        if not structure:
            return f"词书 '{book['title']}' 的章节数据加载失败。"
        # Fetch user chapter progress for this book
        ch_progress = {
            str(cp.chapter_id): cp
            for cp in UserChapterProgress.query.filter_by(user_id=user_id, book_id=book_id).all()
        }
        lines = []
        for ch in structure.get('chapters', []):
            cid = str(ch.get('id', ''))
            cp = ch_progress.get(cid)
            if cp:
                total = cp.correct_count + cp.wrong_count
                acc = round(cp.correct_count / total * 100) if total > 0 else 0
                status = f"已完成 正确率{acc}%" if cp.is_completed else f"进行中 已答{total}题 正确率{acc}%"
            else:
                status = "未开始"
            lines.append(f"  第{ch['id']}章《{ch.get('title', '')}》 {ch.get('word_count', '?')}词 — {status}")
        total_w = structure.get('total_words', 0)
        total_c = structure.get('total_chapters', len(lines))
        done_c = sum(1 for cp in ch_progress.values() if cp.is_completed)
        return (
            f"{book['title']}（共{total_c}章、{total_w}词，已完成{done_c}章）：\n"
            + "\n".join(lines)
        )
    return handler


@ai_bp.route('/ask', methods=['POST'])
@token_required
def ask(current_user: User):
    """
    Chat endpoint — accepts user message + optional learning context.
    Handles tool calls (web search) and returns structured response with options.
    """
    body = request.get_json() or {}
    user_message = body.get('message', '').strip()
    frontend_context = body.get('context', {})  # {currentWord, practiceMode, sessionProgress, ...}

    import logging
    logging.warning(f"[AI] ask from user={current_user.id}: msg='{user_message[:50]}' ctx={frontend_context}")

    if not user_message:
        return jsonify({'error': 'Message is required'}), 400

    # Build messages for LLM
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Inject persistent user data (learning summary)
    try:
        ctx_data = _get_context_data(current_user.id)
        context_msg = _build_learning_context_msg(ctx_data, frontend_context)
        messages.append({"role": "user", "content": f"[学习数据]\n{context_msg}"})
    except Exception as e:
        logging.warning(f"[AI] Failed to fetch user context: {e}")
        messages.append({"role": "user", "content": "[学习数据]\n数据加载失败，请根据用户当前状态回复。"})
        # Still inject frontend context if available
        if frontend_context:
            ctx_str = _build_context_msg(frontend_context)
            messages.append({"role": "user", "content": f"[当前学习状态]\n{ctx_str}"})

    # Load and append conversation history so AI remembers past turns
    history = _load_history(current_user.id)
    messages.extend(history)

    related_notes_msg = _build_related_notes_msg(
        _collect_related_learning_notes(current_user.id, user_message, frontend_context)
    )
    if related_notes_msg:
        messages.append({"role": "user", "content": related_notes_msg})

    # Proactive search: if user asks about examples/definitions, search first
    search_trigger_keywords = ['例句', '例 子', 'example', '怎么 用', '用法', '这个词', '这个词的', '这个单词']
    needs_search = any(kw in user_message for kw in search_trigger_keywords)

    if needs_search and frontend_context.get('currentWord'):
        word = frontend_context['currentWord']
        search_query = f"{word} example sentences IELTS context"
        try:
            from services.llm import web_search
            search_results = web_search(search_query)
            messages.append({"role": "user", "content": (
                f"[网页搜索结果 for '{word}']\n{search_results}\n\n"
                "请根据搜索结果，为用户解释这个单词的用法并给出例句。"
            )})
        except Exception:
            messages.append({"role": "user", "content": user_message})
    else:
        messages.append({"role": "user", "content": user_message})

    # Build per-request handlers that close over current_user.id
    def _handle_remember(note: str, category: str = 'other') -> str:
        return _add_memory_note(current_user.id, note, category)

    extra_handlers = {
        'remember_user_note': _handle_remember,
        'get_wrong_words': _make_get_wrong_words(current_user.id),
        'get_chapter_words': _make_get_chapter_words(current_user.id),
        'get_book_chapters': _make_get_book_chapters(current_user.id),
    }

    # Run chat with tool calling support — capped at 90 s total to prevent hangs
    try:
        import eventlet
        with eventlet.Timeout(90, RuntimeError('LLM timeout')):
            response = _chat_with_tools(messages, tools=TOOLS, extra_handlers=extra_handlers)

        final_text = response.get("text", str(response))
        options = _parse_options(final_text)
        # Strip [options] blocks from the visible reply text
        clean_reply = _strip_options(final_text)

        # Persist this turn so future calls include it as history
        _save_turn(current_user.id, user_message, clean_reply)

        # Auto-save Q&A as a learning note for the journal
        try:
            word_ctx = frontend_context.get('currentWord') if frontend_context else None
            note = UserLearningNote(
                user_id=current_user.id,
                question=user_message,
                answer=clean_reply,
                word_context=word_ctx,
            )
            db.session.add(note)
            db.session.commit()
        except Exception as note_err:
            db.session.rollback()
            logging.warning(f"[AI] Failed to save learning note: {note_err}")

        # Trigger background summarization asynchronously (non-blocking)
        try:
            import eventlet
            eventlet.spawn(_maybe_summarize_history, current_user.id)
        except Exception:
            pass

        return jsonify({
            'reply': clean_reply,
            'options': options,
        })

    except Exception as e:
        import logging as _log
        _log.error(f"[AI] /ask error for user={current_user.id}: {e}", exc_info=True)
        return jsonify({'error': 'AI 服务暂时不可用，请稍后重试'}), 500


# ── POST /api/ai/generate-book ───────────────────────────────────────────────

GENERATE_BOOK_PROMPT = """你是一个 IELTS 词汇专家。用户希望生成一份自定义词汇书，请根据以下信息生成词表。

要求：
1. 返回 JSON 格式，包含 title、description、chapters（数组）、words（数组）
2. 每个 word 必须包含：word（单词）、phonetic（音标，如 /əˈbdev/）、pos（词性，如 n.、v.、adj.）、definition（中文释义）
3. 章节数建议 3-5 章，每章 15-30 个词
4. 词汇要真实存在，是 IELTS 考试常见词汇
5. 不要与用户已掌握的词重复
6. 如果用户指定了 focusAreas（focusAreas），优先选择对应领域的词汇
7. 如果用户指定了 userLevel，按对应难度选词：
   - beginner：大学英语四级水平词汇为主
   - intermediate：六级到雅思核心词汇
   - advanced：雅思高分段学术词汇

输出格式（只需要 JSON，不要其他文字）：
{{
  "title": "词书标题",
  "description": "词书描述（20字内）",
  "chapters": [
    {{ "id": "ch1", "title": "第一章标题", "wordCount": 25 }}
  ],
  "words": [
    {{ "chapterId": "ch1", "word": "abdicate", "phonetic": "/ˈæbdɪkeɪt/", "pos": "v.", "definition": "退位；放弃（职位）" }}
  ]
}}
"""


@ai_bp.route('/generate-book', methods=['POST'])
@token_required
def generate_book(current_user: User):
    """Generate a custom vocabulary book based on user's learning profile."""
    body = request.get_json() or {}
    target_words = body.get('targetWords', 100)
    user_level = body.get('userLevel', 'intermediate')
    focus_areas = body.get('focusAreas', [])
    exclude_words = body.get('excludeWords', [])

    # Build context
    try:
        ctx = _get_context_data(current_user.id)
        wrong_words = ctx.get('wrongWords', [])
        wrong_word_list = [w['word'] for w in wrong_words[:30]]
        all_exclude = list(set(exclude_words + wrong_word_list))
    except Exception:
        all_exclude = exclude_words

    user_message = (
        f"请生成一份约 {target_words} 词的自定义词书。\n"
        f"用户水平：{user_level}\n"
        f"重点领域：{', '.join(focus_areas) if focus_areas else '综合'}"
    )
    if all_exclude:
        user_message += f"\n以下词汇已掌握，请排除：{', '.join(all_exclude[:50])}"

    messages = [
        {"role": "system", "content": GENERATE_BOOK_PROMPT},
        {"role": "user", "content": user_message}
    ]

    try:
        raw = chat(messages, max_tokens=8192)
        raw_text = raw.get('text', '') if isinstance(raw, dict) else str(raw)

        # Parse JSON from response (may be wrapped in markdown code blocks)
        import re
        json_str = re.search(r'\{[\s\S]*\}', raw_text)
        if not json_str:
            return jsonify({'error': 'Failed to parse generated book data'}), 500

        data = json.loads(json_str.group())

        # Persist to DB
        book_id = f"custom_{uuid.uuid4().hex[:12]}"
        book = CustomBook(
            id=book_id,
            user_id=current_user.id,
            title=data.get('title', '自定义词书'),
            description=data.get('description', ''),
            word_count=len(data.get('words', []))
        )
        db.session.add(book)

        chapter_map = {}
        for ch in data.get('chapters', []):
            chapter = CustomBookChapter(
                id=ch.get('id', f"ch_{uuid.uuid4().hex[:6]}"),
                book_id=book_id,
                title=ch.get('title', '未命名章节'),
                word_count=ch.get('wordCount', 0),
                sort_order=data.get('chapters', []).index(ch)
            )
            db.session.add(chapter)
            chapter_map[chapter.id] = chapter

        for w in data.get('words', []):
            word = CustomBookWord(
                chapter_id=w.get('chapterId', list(chapter_map.keys())[0] if chapter_map else 'ch1'),
                word=w.get('word', ''),
                phonetic=w.get('phonetic', ''),
                pos=w.get('pos', ''),
                definition=w.get('definition', '')
            )
            db.session.add(word)

        db.session.commit()

        return jsonify({
            'bookId': book_id,
            'title': book.title,
            'description': book.description,
            'chapters': [c.to_dict() for c in book.chapters],
            'words': [w.to_dict() for w in CustomBookWord.query.filter(
                CustomBookWord.chapter_id.in_([c.id for c in book.chapters])
            ).all()]
        })

    except json.JSONDecodeError as e:
        return jsonify({'error': f'Failed to parse generated book: {str(e)}'}), 500
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Book generation failed: {str(e)}'}), 500


# ── GET /api/ai/custom-books ────────────────────────────────────────────────

@ai_bp.route('/custom-books', methods=['GET'])
@token_required
def list_custom_books(current_user: User):
    """List all AI-generated custom books for the current user."""
    books = CustomBook.query.filter_by(user_id=current_user.id).order_by(
        CustomBook.created_at.desc()
    ).all()
    return jsonify({'books': [b.to_dict() for b in books]})


# ── GET /api/ai/custom-books/<book_id> ───────────────────────────────────────

@ai_bp.route('/custom-books/<book_id>', methods=['GET'])
@token_required
def get_custom_book(current_user: User, book_id: str):
    """Get a single custom book with its chapters and words."""
    book = CustomBook.query.filter_by(id=book_id, user_id=current_user.id).first()
    if not book:
        return jsonify({'error': 'Book not found'}), 404
    return jsonify(book.to_dict())


# ── GET /api/wrong-words ─────────────────────────────────────────────────────

@ai_bp.route('/wrong-words', methods=['GET'])
@token_required
def get_wrong_words(current_user: User):
    """Get all wrong words for the current user from the backend."""
    words = UserWrongWord.query.filter_by(user_id=current_user.id)\
        .order_by(UserWrongWord.wrong_count.desc()).all()
    return jsonify({'words': [w.to_dict() for w in words]}), 200


# ── POST /api/wrong-words/sync ──────────────────────────────────────────────

@ai_bp.route('/wrong-words/sync', methods=['POST'])
@token_required
def sync_wrong_words(current_user: User):
    """Sync wrong words from client localStorage to backend DB."""
    body = request.get_json() or {}
    words = body.get('words', [])

    if not isinstance(words, list):
        return jsonify({'error': 'words must be an array'}), 400

    updated = 0
    for w in words:
        if not w.get('word'):
            continue
        existing = UserWrongWord.query.filter_by(
            user_id=current_user.id,
            word=w['word']
        ).first()
        if existing:
            existing.phonetic = w.get('phonetic') or existing.phonetic
            existing.pos = w.get('pos') or existing.pos
            existing.definition = w.get('definition') or existing.definition
            existing.wrong_count = w.get('wrongCount', existing.wrong_count + 1)
            # Overwrite dimension stats if provided (client sends latest snapshot)
            if 'listeningCorrect' in w:
                existing.listening_correct = w['listeningCorrect']
                existing.listening_wrong   = w.get('listeningWrong', 0)
                existing.meaning_correct   = w.get('meaningCorrect', 0)
                existing.meaning_wrong     = w.get('meaningWrong', 0)
                existing.dictation_correct = w.get('dictationCorrect', 0)
                existing.dictation_wrong   = w.get('dictationWrong', 0)
        else:
            new_w = UserWrongWord(
                user_id=current_user.id,
                word=w['word'],
                phonetic=w.get('phonetic'),
                pos=w.get('pos'),
                definition=w.get('definition'),
                wrong_count=w.get('wrongCount', 1),
                listening_correct=w.get('listeningCorrect', 0),
                listening_wrong=w.get('listeningWrong', 0),
                meaning_correct=w.get('meaningCorrect', 0),
                meaning_wrong=w.get('meaningWrong', 0),
                dictation_correct=w.get('dictationCorrect', 0),
                dictation_wrong=w.get('dictationWrong', 0),
            )
            db.session.add(new_w)
        updated += 1

    db.session.commit()
    return jsonify({'updated': updated})


@ai_bp.route('/wrong-words/<word>', methods=['DELETE'])
@token_required
def delete_wrong_word(current_user: User, word: str):
    """Delete a wrong word by word string."""
    record = UserWrongWord.query.filter_by(user_id=current_user.id, word=word).first()
    if record:
        db.session.delete(record)
        db.session.commit()
    return jsonify({'message': '已移除'}), 200


@ai_bp.route('/wrong-words', methods=['DELETE'])
@token_required
def clear_wrong_words(current_user: User):
    """Clear all wrong words for the current user."""
    UserWrongWord.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    return jsonify({'message': '已清空'}), 200


# ── POST /api/ai/log-session ─────────────────────────────────────────────────

@ai_bp.route('/learning-stats', methods=['GET'])
@token_required
def get_learning_stats(current_user: User):
    """Return daily aggregated learning stats from study sessions, with optional filters."""
    from datetime import datetime, timedelta
    from collections import defaultdict

    days = min(int(request.args.get('days', 30)), 90)
    book_id_filter = request.args.get('book_id') or None
    mode_filter = request.args.get('mode') or None

    since = datetime.utcnow() - timedelta(days=days)

    query = UserStudySession.query.filter(
        UserStudySession.user_id == current_user.id,
        UserStudySession.started_at >= since
    )
    if book_id_filter:
        query = query.filter(UserStudySession.book_id == book_id_filter)
    if mode_filter:
        query = query.filter(UserStudySession.mode == mode_filter)

    sessions = query.all()

    # Aggregate by calendar date
    daily = defaultdict(lambda: {
        'words_studied': 0, 'correct_count': 0,
        'wrong_count': 0, 'duration_seconds': 0, 'sessions': 0
    })
    for s in sessions:
        date_key = s.started_at.strftime('%Y-%m-%d')
        daily[date_key]['words_studied'] += s.words_studied or 0
        daily[date_key]['correct_count'] += s.correct_count or 0
        daily[date_key]['wrong_count'] += s.wrong_count or 0
        daily[date_key]['duration_seconds'] += s.duration_seconds or 0
        daily[date_key]['sessions'] += 1

    # Build full date range (oldest → newest)
    result = []
    for i in range(days):
        d = (datetime.utcnow() - timedelta(days=days - 1 - i)).strftime('%Y-%m-%d')
        day_data = dict(daily.get(d, {
            'words_studied': 0, 'correct_count': 0,
            'wrong_count': 0, 'duration_seconds': 0, 'sessions': 0
        }))
        total = day_data['correct_count'] + day_data['wrong_count']
        day_data['accuracy'] = round(day_data['correct_count'] / total * 100) if total > 0 else None
        result.append({'date': d, **day_data})

    # ── Chapter-progress fallback (when UserStudySession is sparse/empty) ──────
    # Group UserChapterProgress by updated_at date; use words_learned as proxy
    # for words studied that day. Not perfect for multi-day chapters, but much
    # better than showing zeros when the user has real learning history.
    chapter_q = UserChapterProgress.query.filter(
        UserChapterProgress.user_id == current_user.id,
        UserChapterProgress.updated_at >= since,
    )
    if book_id_filter:
        chapter_q = chapter_q.filter(UserChapterProgress.book_id == book_id_filter)
    chapter_rows = chapter_q.all()

    ch_daily: dict = defaultdict(lambda: {'words_studied': 0, 'correct_count': 0, 'wrong_count': 0})
    for cp in chapter_rows:
        dk = cp.updated_at.strftime('%Y-%m-%d')
        ch_daily[dk]['words_studied'] += cp.words_learned or 0
        ch_daily[dk]['correct_count'] += cp.correct_count or 0
        ch_daily[dk]['wrong_count'] += cp.wrong_count or 0

    fallback_result = []
    for i in range(days):
        d = (datetime.utcnow() - timedelta(days=days - 1 - i)).strftime('%Y-%m-%d')
        fd = dict(ch_daily.get(d, {'words_studied': 0, 'correct_count': 0, 'wrong_count': 0}))
        t = fd['correct_count'] + fd['wrong_count']
        fd['accuracy'] = round(fd['correct_count'] / t * 100) if t > 0 else None
        fd['duration_seconds'] = 0
        fd['sessions'] = 0
        fallback_result.append({'date': d, **fd})

    # Decide which daily series to return (sessions preferred)
    has_session_data = any(d['sessions'] > 0 for d in result)
    active_daily = result if has_session_data else fallback_result
    use_fallback = not has_session_data

    # Books and modes the user has ever studied (for filter dropdowns)
    all_sessions = UserStudySession.query.filter_by(user_id=current_user.id).all()
    book_ids_from_sessions = {s.book_id for s in all_sessions if s.book_id}
    # Also include books from chapter progress (covers users with no sessions yet)
    all_chapters = UserChapterProgress.query.filter_by(user_id=current_user.id).all()
    book_ids_from_chapters = {cp.book_id for cp in all_chapters if cp.book_id}
    book_ids = list(book_ids_from_sessions | book_ids_from_chapters)
    modes_used = sorted({s.mode for s in all_sessions if s.mode})

    try:
        from routes.books import VOCAB_BOOKS
        book_title_map = {b['id']: b['title'] for b in VOCAB_BOOKS}
    except Exception:
        book_title_map = {}

    books = [{'id': bid, 'title': book_title_map.get(bid, bid)} for bid in book_ids]

    # Overall summary for the period (use fallback totals when no sessions)
    total_words = sum(d['words_studied'] for d in active_daily)
    total_duration = sum(d['duration_seconds'] for d in active_daily)
    total_correct = sum(d['correct_count'] for d in active_daily)
    total_wrong = sum(d['wrong_count'] for d in active_daily)
    total_sessions = sum(d['sessions'] for d in active_daily)
    total_attempted = total_correct + total_wrong
    period_accuracy = round(total_correct / total_attempted * 100) if total_attempted > 0 else None

    # All-time totals from chapter progress（words_learned 按章相加可能与「全局不重复词」不一致）
    all_chapter_progress = UserChapterProgress.query.filter_by(user_id=current_user.id).all()
    chapter_words_sum = sum(cp.words_learned or 0 for cp in all_chapter_progress)
    alltime_words = _alltime_words_display(current_user.id, chapter_words_sum)
    alltime_correct = sum(cp.correct_count or 0 for cp in all_chapter_progress)
    alltime_wrong = sum(cp.wrong_count or 0 for cp in all_chapter_progress)
    alltime_attempted = alltime_correct + alltime_wrong
    alltime_accuracy = round(alltime_correct / alltime_attempted * 100) if alltime_attempted > 0 else None

    # Today's accuracy from chapter progress updated today
    today_str = datetime.utcnow().strftime('%Y-%m-%d')
    today_chapters = [cp for cp in all_chapter_progress
                      if cp.updated_at and cp.updated_at.strftime('%Y-%m-%d') == today_str]
    today_correct = sum(cp.correct_count or 0 for cp in today_chapters)
    today_wrong = sum(cp.wrong_count or 0 for cp in today_chapters)
    today_attempted = today_correct + today_wrong
    today_accuracy = round(today_correct / today_attempted * 100) if today_attempted > 0 else None

    # Session-based duration (only meaningful when sessions exist)
    all_user_sessions = UserStudySession.query.filter_by(user_id=current_user.id).all()
    alltime_duration = sum(s.duration_seconds or 0 for s in all_user_sessions)
    today_sessions = [s for s in all_user_sessions
                      if s.started_at and s.started_at.strftime('%Y-%m-%d') == today_str]
    today_duration = sum(s.duration_seconds or 0 for s in today_sessions)

    # ── Per-mode breakdown (all-time, from UserStudySession) ──────────────────
    # 默认 words_studied 按会话累加：同一词在不同模式练习会重复计入；各模式相加通常 > 全局「累计学习新词数」。
    # 速记模式单独用 user_quick_memory_records 行数（每词一行）覆盖，与会话累加口径区分。
    # 跳过 mode 为空的记录：start-session 创建时未写 mode，若 log-session 未带 mode 会一直是 NULL，不应显示为 unknown
    mode_stats: dict = {}
    for s in all_user_sessions:
        m = (s.mode or '').strip()
        if not m:
            continue
        if m not in mode_stats:
            mode_stats[m] = {
                'mode': m,
                'words_studied': 0, 'correct_count': 0,
                'wrong_count': 0, 'duration_seconds': 0, 'sessions': 0,
            }
        mode_stats[m]['words_studied'] += s.words_studied or 0
        mode_stats[m]['correct_count'] += s.correct_count or 0
        mode_stats[m]['wrong_count'] += s.wrong_count or 0
        mode_stats[m]['duration_seconds'] += s.duration_seconds or 0
        mode_stats[m]['sessions'] += 1

    for md in mode_stats.values():
        attempted = md['correct_count'] + md['wrong_count']
        md['attempts'] = attempted
        md['accuracy'] = round(md['correct_count'] / attempted * 100) if attempted > 0 else None
        sess = md['sessions'] or 0
        md['avg_words_per_session'] = round(md['words_studied'] / sess, 1) if sess else 0.0

    qm_extra = _quick_memory_word_stats(current_user.id)
    qm_total = int(qm_extra.get('qm_word_total') or 0)
    if qm_total > 0:
        if 'quickmemory' not in mode_stats:
            mode_stats['quickmemory'] = {
                'mode': 'quickmemory',
                'words_studied': 0,
                'correct_count': 0,
                'wrong_count': 0,
                'duration_seconds': 0,
                'sessions': 0,
            }
        mode_stats['quickmemory']['words_studied'] = qm_total
        qm_sess = mode_stats['quickmemory']['sessions'] or 0
        mode_stats['quickmemory']['avg_words_per_session'] = (
            round(qm_total / qm_sess, 1) if qm_sess else 0.0
        )

    mode_breakdown = sorted(mode_stats.values(), key=lambda x: x['words_studied'], reverse=True)

    wrong_top = UserWrongWord.query.filter_by(user_id=current_user.id).order_by(
        UserWrongWord.wrong_count.desc()
    ).limit(10).all()
    wrong_top10 = [
        {
            'word': w.word,
            'wrong_count': w.wrong_count or 0,
            'phonetic': w.phonetic or '',
            'pos': w.pos or '',
            'listening_wrong': w.listening_wrong or 0,
            'meaning_wrong': w.meaning_wrong or 0,
            'dictation_wrong': w.dictation_wrong or 0,
        }
        for w in wrong_top
    ]

    chapter_title_cache: dict = {}
    chapter_breakdown = []
    for cp in all_chapter_progress:
        if (cp.correct_count or 0) + (cp.wrong_count or 0) == 0 and (cp.words_learned or 0) == 0:
            continue
        bid = cp.book_id
        if bid not in chapter_title_cache:
            chapter_title_cache[bid] = _chapter_title_map(bid)
        ch_titles = chapter_title_cache[bid]
        ch_key = str(cp.chapter_id)
        tot = (cp.correct_count or 0) + (cp.wrong_count or 0)
        chapter_breakdown.append({
            'book_id': bid,
            'book_title': book_title_map.get(bid, bid),
            'chapter_id': cp.chapter_id,
            'chapter_title': ch_titles.get(ch_key, f'Chapter {cp.chapter_id}'),
            'words_learned': cp.words_learned or 0,
            'correct': cp.correct_count or 0,
            'wrong': cp.wrong_count or 0,
            'accuracy': round((cp.correct_count or 0) / tot * 100) if tot > 0 else None,
        })
    chapter_breakdown.sort(key=lambda x: (x['book_id'], x['chapter_id']))

    chapter_mode_stats = []
    for mp in UserChapterModeProgress.query.filter_by(user_id=current_user.id).all():
        t = (mp.correct_count or 0) + (mp.wrong_count or 0)
        if t == 0:
            continue
        mb = mp.book_id
        if mb not in chapter_title_cache:
            chapter_title_cache[mb] = _chapter_title_map(mb)
        ch_tmap = chapter_title_cache[mb]
        chapter_mode_stats.append({
            'book_id': mb,
            'book_title': book_title_map.get(mb, mb),
            'chapter_id': mp.chapter_id,
            'chapter_title': ch_tmap.get(str(mp.chapter_id), f'Chapter {mp.chapter_id}'),
            'mode': mp.mode,
            'correct': mp.correct_count or 0,
            'wrong': mp.wrong_count or 0,
            'accuracy': round((mp.correct_count or 0) / t * 100),
        })
    chapter_mode_stats.sort(key=lambda x: (x['book_id'], x['chapter_id'], x['mode']))

    pie_chart = [
        {'mode': m['mode'], 'value': m['words_studied'], 'sessions': m['sessions']}
        for m in mode_breakdown
    ]

    # 计算 streak_days
    streak_days = _calc_streak_days(current_user.id)

    # 计算最弱模式（正确率最低且有足够样本的）
    weakest_mode = None
    for md in mode_breakdown:
        acc = md.get('accuracy')
        if acc is not None and md.get('attempts', 0) >= 5:
            if weakest_mode is None or acc < (weakest_mode[1] or 100):
                weakest_mode = (md['mode'], acc)

    # 计算 trend_direction（基于最近14天 vs 前14天对比）
    trend_direction = 'stable'
    if len(result) >= 14:
        recent = result[-7:] if len(result) >= 7 else result[-len(result):]
        older = result[-14:-7] if len(result) >= 14 else result[:-7]
        if older:
            recent_acc = [d['accuracy'] for d in recent if d.get('accuracy') is not None]
            older_acc = [d['accuracy'] for d in older if d.get('accuracy') is not None]
            if recent_acc and older_acc:
                avg_recent = sum(recent_acc) / len(recent_acc)
                avg_older = sum(older_acc) / len(older_acc)
                if avg_recent > avg_older + 5:
                    trend_direction = 'improving'
                elif avg_recent < avg_older - 5:
                    trend_direction = 'declining'

    return jsonify({
        'daily': active_daily,
        'books': books,
        'modes': modes_used,
        'use_fallback': use_fallback,
        'summary': {
            'total_words': total_words,
            'total_duration_seconds': total_duration,
            'total_sessions': total_sessions,
            'accuracy': period_accuracy,
        },
        'alltime': {
            'total_words': alltime_words,
            'accuracy': alltime_accuracy,
            'duration_seconds': alltime_duration,
            'today_accuracy': today_accuracy,
            'today_duration_seconds': today_duration,
            'today_new_words': qm_extra['today_new_words'],
            'today_review_words': qm_extra['today_review_words'],
            'alltime_review_words': qm_extra['alltime_review_words'],
            'cumulative_review_events': qm_extra['cumulative_review_events'],
            'ebbinghaus_rate': qm_extra['ebbinghaus_rate'],
            'ebbinghaus_due_total': qm_extra['ebbinghaus_due_total'],
            'ebbinghaus_met': qm_extra['ebbinghaus_met'],
            'qm_word_total': qm_extra['qm_word_total'],
            'ebbinghaus_stages': qm_extra['ebbinghaus_stages'],
            'upcoming_reviews_3d': qm_extra.get('upcoming_reviews_3d', 0),
            'streak_days': streak_days,
            'weakest_mode': weakest_mode[0] if weakest_mode else None,
            'weakest_mode_accuracy': weakest_mode[1] if weakest_mode else None,
            'trend_direction': trend_direction,
        },
        'mode_breakdown': mode_breakdown,
        'pie_chart': pie_chart,
        'wrong_top10': wrong_top10,
        'chapter_breakdown': chapter_breakdown,
        'chapter_mode_stats': chapter_mode_stats,
    })


@ai_bp.route('/start-session', methods=['POST'])
@token_required
def start_session(current_user: User):
    """Create a session record with server-side start time; returns sessionId for later completion.

    Client should send mode + optional bookId/chapterId so rows are not left with NULL mode
    (vocabulary source: book chapter API, whole book, 30-day plan, or wrong-words list — see PracticePage).
    """
    body = request.get_json() or {}
    mode_raw = (body.get('mode') or 'smart')
    if isinstance(mode_raw, str):
        mode = mode_raw.strip()[:30] or 'smart'
    else:
        mode = 'smart'
    book_id = body.get('bookId') or None
    ch = body.get('chapterId')
    chapter_id = str(ch) if ch is not None and str(ch).strip() != '' else None

    session = UserStudySession(
        user_id=current_user.id,
        mode=mode,
        book_id=book_id,
        chapter_id=chapter_id,
        started_at=datetime.utcnow(),
    )
    db.session.add(session)
    db.session.commit()
    return jsonify({'sessionId': session.id}), 201


@ai_bp.route('/cancel-session', methods=['POST'])
@token_required
def cancel_session(current_user: User):
    """Delete a started session when no meaningful learning interaction happened."""
    body = request.get_json() or {}
    session_id = body.get('sessionId')
    if not session_id:
        return jsonify({'error': 'sessionId is required'}), 400

    session = UserStudySession.query.filter_by(
        id=session_id,
        user_id=current_user.id,
    ).first()
    if not session:
        return jsonify({'error': 'Session not found'}), 404

    has_meaningful_data = any([
        (session.words_studied or 0) > 0,
        (session.correct_count or 0) > 0,
        (session.wrong_count or 0) > 0,
        (session.duration_seconds or 0) > 0,
    ])
    if has_meaningful_data:
        return jsonify({'error': 'Session already contains learning data'}), 409

    db.session.delete(session)
    db.session.commit()
    return jsonify({'deleted': True}), 200


@ai_bp.route('/log-session', methods=['POST'])
@token_required
def log_session(current_user: User):
    """Persist a study session record to the database.

    If sessionId is provided the existing session row (created by /start-session) is
    updated and duration_seconds is calculated server-side from started_at → now.
    Otherwise a new row is inserted using the client-supplied durationSeconds.
    """
    body = request.get_json() or {}
    try:
        session_id = body.get('sessionId')
        if session_id:
            # Update the existing session row created by /start-session
            session = UserStudySession.query.filter_by(
                id=session_id, user_id=current_user.id
            ).first()
            if session:
                ended_at = datetime.utcnow()
                session.ended_at = ended_at
                computed_duration = max(0, int((ended_at - session.started_at).total_seconds()))
                if body.get('mode'):
                    session.mode = body['mode']
                session.book_id = body.get('bookId', session.book_id)
                session.chapter_id = body.get('chapterId', session.chapter_id)
                session.words_studied = body.get('wordsStudied', 0)
                session.correct_count = body.get('correctCount', 0)
                session.wrong_count = body.get('wrongCount', 0)
                # Sessions that already contain meaningful study activity should not
                # end up recorded as 0s just because start/end landed in the same second.
                if computed_duration == 0 and (
                    (session.words_studied or 0) > 0 or
                    (session.correct_count or 0) > 0 or
                    (session.wrong_count or 0) > 0
                ):
                    session.duration_seconds = 1
                else:
                    session.duration_seconds = computed_duration
                db.session.commit()
                return jsonify({'id': session.id}), 200

        # Fallback: create a new row using client-supplied timestamps/duration
        started_at = None
        client_start = body.get('startedAt')
        if client_start:
            try:
                from datetime import timezone
                started_at = datetime.fromtimestamp(int(client_start) / 1000, tz=timezone.utc).replace(tzinfo=None)
            except Exception:
                pass

        duration_seconds = body.get('durationSeconds', 0) or 0
        words_studied = body.get('wordsStudied', 0) or 0
        correct_count = body.get('correctCount', 0) or 0
        wrong_count = body.get('wrongCount', 0) or 0
        if duration_seconds == 0 and (words_studied > 0 or correct_count > 0 or wrong_count > 0):
            duration_seconds = 1

        session = UserStudySession(
            user_id=current_user.id,
            mode=body.get('mode') or None,
            book_id=body.get('bookId'),
            chapter_id=body.get('chapterId'),
            words_studied=words_studied,
            correct_count=correct_count,
            wrong_count=wrong_count,
            duration_seconds=duration_seconds,
        )
        if started_at:
            session.started_at = started_at
        db.session.add(session)
        db.session.commit()
        return jsonify({'id': session.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ── GET /api/ai/quick-memory ──────────────────────────────────────────────────

@ai_bp.route('/quick-memory', methods=['GET'])
@token_required
def get_quick_memory(current_user: User):
    """Return all quick-memory records for the current user."""
    records = UserQuickMemoryRecord.query.filter_by(user_id=current_user.id).all()
    return jsonify({'records': [r.to_dict() for r in records]}), 200


# ── GET /api/ai/quick-memory/review-queue ────────────────────────────────────

@ai_bp.route('/quick-memory/review-queue', methods=['GET'])
@token_required
def get_quick_memory_review_queue(current_user: User):
    """Return the user's due/upcoming Ebbinghaus review queue with full word metadata."""
    try:
        limit = max(1, min(int(request.args.get('limit', 20)), 100))
    except (TypeError, ValueError):
        limit = 20

    try:
        within_days = max(1, min(int(request.args.get('within_days', 1)), 30))
    except (TypeError, ValueError):
        within_days = 1

    now_ms = int(time.time() * 1000)
    window_end_ms = now_ms + within_days * 86400000

    pool = _get_global_vocab_pool()
    pool_by_word = {
        (item.get('word') or '').strip().lower(): item
        for item in pool
        if (item.get('word') or '').strip()
    }

    due_words = []
    upcoming_words = []

    rows = (
        UserQuickMemoryRecord.query
        .filter_by(user_id=current_user.id)
        .filter(UserQuickMemoryRecord.next_review > 0)
        .order_by(UserQuickMemoryRecord.next_review.asc())
        .all()
    )

    for row in rows:
        word_key = (row.word or '').strip().lower()
        vocab_item = pool_by_word.get(word_key)
        if not vocab_item:
            continue

        next_review = row.next_review or 0
        if next_review <= now_ms:
            due_state = 'due'
        elif next_review <= window_end_ms:
            due_state = 'upcoming'
        else:
            continue

        item = {
            **vocab_item,
            'status': row.status,
            'knownCount': row.known_count or 0,
            'unknownCount': row.unknown_count or 0,
            'nextReview': next_review,
            'dueState': due_state,
        }
        if due_state == 'due':
            due_words.append(item)
        else:
            upcoming_words.append(item)

    selected = due_words[:limit]
    if len(selected) < limit:
        selected.extend(upcoming_words[:limit - len(selected)])

    return jsonify({
        'words': selected,
        'summary': {
            'due_count': len(due_words),
            'upcoming_count': len(upcoming_words),
            'returned_count': len(selected),
            'review_window_days': within_days,
        },
    }), 200


# ── POST /api/ai/quick-memory/sync ───────────────────────────────────────────

@ai_bp.route('/quick-memory/sync', methods=['POST'])
@token_required
def sync_quick_memory(current_user: User):
    """Bulk upsert quick-memory records. Accepts {records: [{word, status, firstSeen, lastSeen, knownCount, unknownCount, nextReview}]}."""
    body = request.get_json() or {}
    records_in = body.get('records', [])
    if not isinstance(records_in, list):
        return jsonify({'error': 'records must be a list'}), 400

    for r in records_in:
        word = (r.get('word') or '').strip().lower()
        if not word:
            continue
        existing = UserQuickMemoryRecord.query.filter_by(
            user_id=current_user.id, word=word
        ).first()
        if existing:
            # Only overwrite if client data is newer (lastSeen is epoch ms)
            if (r.get('lastSeen') or 0) >= (existing.last_seen or 0):
                existing.status        = r.get('status', existing.status)
                existing.first_seen    = r.get('firstSeen', existing.first_seen)
                existing.last_seen     = r.get('lastSeen', existing.last_seen)
                existing.known_count   = r.get('knownCount', existing.known_count)
                existing.unknown_count = r.get('unknownCount', existing.unknown_count)
                existing.next_review   = r.get('nextReview', existing.next_review)
                # fuzzy_count: take the max so it never decreases
                if r.get('fuzzyCount') is not None:
                    existing.fuzzy_count = max(existing.fuzzy_count or 0, r['fuzzyCount'])
        else:
            new_rec = UserQuickMemoryRecord(
                user_id=current_user.id,
                word=word,
                status=r.get('status', 'unknown'),
                first_seen=r.get('firstSeen', 0),
                last_seen=r.get('lastSeen', 0),
                known_count=r.get('knownCount', 0),
                unknown_count=r.get('unknownCount', 0),
                next_review=r.get('nextReview', 0),
                fuzzy_count=r.get('fuzzyCount', 0),
            )
            db.session.add(new_rec)

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return jsonify({'ok': True}), 200


# ── GET /api/ai/smart-stats ───────────────────────────────────────────────────

@ai_bp.route('/smart-stats', methods=['GET'])
@token_required
def get_smart_stats(current_user: User):
    """Return all smart-mode word stats for the current user."""
    stats = UserSmartWordStat.query.filter_by(user_id=current_user.id).all()
    return jsonify({'stats': [s.to_dict() for s in stats]}), 200


# ── POST /api/ai/smart-stats/sync ─────────────────────────────────────────────

@ai_bp.route('/smart-stats/sync', methods=['POST'])
@token_required
def sync_smart_stats(current_user: User):
    """Bulk upsert smart-mode word stats. Accepts {stats: [{word, listening, meaning, dictation}]}."""
    body = request.get_json() or {}
    stats_in = body.get('stats', [])
    if not isinstance(stats_in, list):
        return jsonify({'error': 'stats must be a list'}), 400

    for s in stats_in:
        word = (s.get('word') or '').strip().lower()
        if not word:
            continue
        listening = s.get('listening') or {}
        meaning   = s.get('meaning')   or {}
        dictation = s.get('dictation') or {}

        existing = UserSmartWordStat.query.filter_by(
            user_id=current_user.id, word=word
        ).first()
        if existing:
            existing.listening_correct = listening.get('correct', existing.listening_correct)
            existing.listening_wrong   = listening.get('wrong',   existing.listening_wrong)
            existing.meaning_correct   = meaning.get('correct',   existing.meaning_correct)
            existing.meaning_wrong     = meaning.get('wrong',     existing.meaning_wrong)
            existing.dictation_correct = dictation.get('correct', existing.dictation_correct)
            existing.dictation_wrong   = dictation.get('wrong',   existing.dictation_wrong)
        else:
            new_stat = UserSmartWordStat(
                user_id=current_user.id,
                word=word,
                listening_correct=listening.get('correct', 0),
                listening_wrong=listening.get('wrong', 0),
                meaning_correct=meaning.get('correct', 0),
                meaning_wrong=meaning.get('wrong', 0),
                dictation_correct=dictation.get('correct', 0),
                dictation_wrong=dictation.get('wrong', 0),
            )
            db.session.add(new_stat)

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return jsonify({'ok': True}), 200
