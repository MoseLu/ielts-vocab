import type { MobileWord, PracticeMode, WrongWord } from './mobileSchemas'

export type PracticeResult = {
  correct: boolean
  expected: string
  feedback: string
}

export type PracticeProgressSnapshot = {
  answeredWords: string[]
  correctCount: number
  currentIndex: number
  isCompleted: boolean
  queueWords: string[]
  wordsLearned: number
  wrongCount: number
}

export const PRACTICE_MODE_LABELS: Record<PracticeMode, string> = {
  smart: '智能模式',
  quickmemory: '速记模式',
  test: '测试模式',
  listening: '听音选义',
  meaning: '默写模式',
  dictation: '听写模式',
  follow: '跟读模式',
  radio: '随身听',
  errors: '错词强化',
}

export function stripHtml(value: string | null | undefined): string {
  return String(value ?? '')
    .replace(/<script[\s\S]*?<\/script>/gi, '')
    .replace(/<style[\s\S]*?<\/style>/gi, '')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&nbsp;/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/\s+/g, ' ')
    .trim()
}

export function normalizeAnswer(value: string | null | undefined): string {
  return stripHtml(value)
    .toLowerCase()
    .replace(/[’']/g, '')
    .replace(/[^a-z0-9]+/g, ' ')
    .trim()
}

export function wordKey(word: Pick<MobileWord, 'word'>): string {
  return normalizeAnswer(word.word)
}

export function buildPracticeOptions(word: MobileWord, vocabulary: MobileWord[]): string[] {
  const correct = word.definition || word.word
  const pool = vocabulary
    .map(item => item.definition || item.word)
    .filter(value => value && value !== correct)
  const unique = [...new Set(pool)].slice(0, 3)
  return shuffle([correct, ...unique]).slice(0, 4)
}

export function evaluatePracticeAnswer(
  word: MobileWord,
  mode: PracticeMode,
  answer: string,
): PracticeResult {
  if (mode === 'quickmemory' || mode === 'test') {
    const correct = answer === 'known'
    return {
      correct,
      expected: word.definition,
      feedback: correct ? '已标记认识' : '已加入复习',
    }
  }

  if (mode === 'listening') {
    const correct = stripHtml(answer) === stripHtml(word.definition)
    return {
      correct,
      expected: word.definition,
      feedback: correct ? '听音辨义正确' : `正确释义：${word.definition}`,
    }
  }

  if (mode === 'follow' || mode === 'radio') {
    return {
      correct: true,
      expected: word.word,
      feedback: mode === 'follow' ? '跟读记录已完成' : '播放进度已记录',
    }
  }

  const expected = word.word
  const correct = normalizeAnswer(answer) === normalizeAnswer(expected)
  return {
    correct,
    expected,
    feedback: correct ? '回答正确' : `正确答案：${expected}`,
  }
}

export function buildProgressSnapshot(params: {
  correctCount: number
  currentIndex: number
  queue: MobileWord[]
  wrongCount: number
}): PracticeProgressSnapshot {
  const answered = params.queue.slice(0, params.currentIndex)
  return {
    answeredWords: answered.map(item => item.word),
    correctCount: params.correctCount,
    currentIndex: params.currentIndex,
    isCompleted: params.currentIndex >= params.queue.length,
    queueWords: params.queue.map(item => item.word),
    wordsLearned: new Set(answered.map(item => wordKey(item))).size,
    wrongCount: params.wrongCount,
  }
}

export function buildWrongWordRecord(word: MobileWord, mode: PracticeMode): WrongWord {
  const dimension = mode === 'listening'
    ? 'listening'
    : mode === 'dictation'
      ? 'dictation'
      : mode === 'follow'
        ? 'speaking'
        : mode === 'quickmemory' || mode === 'test'
          ? 'recognition'
          : 'meaning'
  return {
    ...word,
    ebbinghaus_completed: false,
    ebbinghaus_remaining: 0,
    ebbinghaus_streak: 0,
    last_error_at: new Date().toISOString(),
    mistake_type: dimension,
    recognition_pass_streak: 0,
    wrong_count: 1,
  }
}

export function buildQuickMemorySyncRecord(word: MobileWord, known: boolean, now = Date.now()) {
  const nextReview = now + (known ? 24 * 60 * 60 * 1000 : 15 * 60 * 1000)
  return {
    word: word.word,
    status: known ? 'known' : 'unknown',
    firstSeen: now,
    lastSeen: now,
    knownCount: known ? 1 : 0,
    unknownCount: known ? 0 : 1,
    fuzzyCount: 0,
    nextReview,
    bookId: word.book_id || undefined,
    chapterId: word.chapter_id == null ? undefined : String(word.chapter_id),
  }
}

export function buildCsv(rows: Array<Record<string, string | number | null | undefined>>): string {
  const keys = [...new Set(rows.flatMap(row => Object.keys(row)))]
  const escape = (value: unknown) => `"${String(value ?? '').replace(/"/g, '""')}"`
  return [keys.join(','), ...rows.map(row => keys.map(key => escape(row[key])).join(','))].join('\n')
}

function shuffle<T>(values: T[]): T[] {
  return values
    .map(value => ({ value, sort: Math.random() }))
    .sort((a, b) => a.sort - b.sort)
    .map(item => item.value)
}
