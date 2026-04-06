export interface UserStats {
  total_correct: number
  total_wrong: number
  accuracy: number
  books_in_progress: number
  books_completed: number
  total_study_seconds: number
  total_words_studied: number
  wrong_words_count: number
  session_count: number
  recent_sessions_7d: number
  last_active: string | null
}

export interface AdminUser {
  id: number
  username: string
  email: string
  avatar_url: string | null
  is_admin: boolean
  created_at: string
  stats: UserStats
}

export interface DailyActivity {
  day: string
  sessions: number
  users: number
  study_seconds: number
  words: number
}

export interface ModeStats {
  mode: string
  count: number
  words: number
}

export interface TopBook {
  book_id: string
  sessions: number
  users: number
}

export interface Overview {
  total_users: number
  active_users_today: number
  active_users_7d: number
  new_users_today: number
  new_users_7d: number
  total_sessions: number
  total_study_seconds: number
  total_words_studied: number
  avg_accuracy: number
  daily_activity: DailyActivity[]
  mode_stats: ModeStats[]
  top_books: TopBook[]
}

export interface UserDetail {
  user: AdminUser
  book_progress: Array<{
    book_id: string
    correct_count: number
    wrong_count: number
    is_completed: boolean
    current_index: number
    updated_at: string
  }>
  wrong_words: Array<{
    word: string
    phonetic: string
    pos: string
    definition: string
    wrong_count: number
    last_wrong_at: string | null
    updated_at: string
  }>
  sessions: Array<{
    id: number
    mode: string
    book_id: string
    chapter_id: string
    words_studied: number
    correct_count: number
    wrong_count: number
    accuracy: number
    duration_seconds: number
    started_at: string
    ended_at: string | null
    studied_words: string[]
    studied_words_total: number
  }>
  daily_study: Array<{
    day: string
    seconds: number
    words: number
    correct: number
    wrong: number
  }>
  chapter_daily: Array<{
    book_id: string
    chapter_id: string
    day: string
    mode: string
    sessions: number
    words: number
    correct: number
    wrong: number
    seconds: number
  }>
}

export type AdminTab = 'overview' | 'users'
export type AdminDetailTab = 'progress' | 'wrong_words' | 'sessions' | 'chart' | 'chapter_daily'
export type WrongWordsSort = 'last_error' | 'wrong_count'

export const modeLabels: Record<string, string> = {
  smart: '智能模式',
  listening: '听音选义',
  meaning: '释义拼词',
  dictation: '听写模式',
  radio: '随身听',
  quickmemory: '速记模式',
}

export const bookLabels: Record<string, string> = {
  ielts_reading_premium: '雅思阅读精讲',
  ielts_listening_premium: '雅思听力精讲',
  ielts_comprehensive: '雅思全面词汇',
  ielts_ultimate: '雅思核心词汇',
  awl_academic: '学术词汇表',
}

export function fmtChapterId(chapterId: string | null | undefined): string {
  if (!chapterId) return '全部章节'
  if (/^\d+$/.test(chapterId)) return `第${chapterId}章`
  return chapterId
}

export function fmtSeconds(s: number) {
  if (s < 60) return `${s}秒`
  if (s < 3600) return `${Math.floor(s / 60)}分钟`
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  return m > 0 ? `${h}小时${m}分` : `${h}小时`
}

export function fmtDate(iso: string | null) {
  if (!iso) return '—'
  const d = new Date(iso)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

export function parseDateValue(iso: string | null) {
  if (!iso) return null
  const value = new Date(iso)
  return Number.isNaN(value.getTime()) ? null : value
}

export function fmtTime(iso: string | null) {
  const d = parseDateValue(iso)
  if (!d) return '—'
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

export function fmtDateTime(iso: string | null) {
  const d = parseDateValue(iso)
  if (!d) return '—'
  return `${fmtDate(iso)} ${fmtTime(iso)}`
}

export function resolveSessionEnd(startedAt: string | null, endedAt: string | null, durationSeconds: number) {
  const explicitEnd = parseDateValue(endedAt)
  if (explicitEnd) return explicitEnd

  const start = parseDateValue(startedAt)
  if (!start || durationSeconds <= 0) return null
  return new Date(start.getTime() + durationSeconds * 1000)
}

export function fmtSessionTimeRange(startedAt: string | null, endedAt: string | null, durationSeconds: number) {
  const start = parseDateValue(startedAt)
  if (!start) return '—'

  const end = resolveSessionEnd(startedAt, endedAt, durationSeconds)
  if (!end) return fmtTime(startedAt)
  return `${fmtTime(startedAt)} - ${String(end.getHours()).padStart(2, '0')}:${String(end.getMinutes()).padStart(2, '0')}`
}

export function buildSessionContent(session: UserDetail['sessions'][number]) {
  const parts = [
    bookLabels[session.book_id] || session.book_id || '',
    fmtChapterId(session.chapter_id),
    modeLabels[session.mode] || session.mode || '',
  ].filter(Boolean)
  return parts.join(' · ') || '未记录学习内容'
}

export function buildSessionWordSample(words: string[], total: number) {
  if (!words.length || total <= 0) return '未记录到词样本'
  return total > words.length ? `${words.join('、')} 等${total}个词` : words.join('、')
}
