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
  const currentWordKey = normalizeAnswer(word.word)
  const knownWordKeys = new Set(vocabulary.map(item => normalizeAnswer(item.word)).filter(Boolean))
  const candidates = vocabulary
    .filter(item => {
      const candidateKey = normalizeAnswer(item.word)
      if (!candidateKey || candidateKey === currentWordKey) return false
      if (isListeningInflectionCandidate(item, knownWordKeys)) return false
      return true
    })
    .map((item, index) => ({
      item,
      index,
      score: listeningDistractorScore(word, item),
    }))
    .sort((left, right) => {
      const scoreDelta = right.score - left.score
      return scoreDelta !== 0 ? scoreDelta : left.index - right.index
    })
  const strongCandidates = candidates.filter(({ item }) => isStrongListeningDistractor(word, item))
  const pool = (strongCandidates.length >= 3 ? strongCandidates : candidates)
    .map(({ item }) => item.definition || item.word)
    .filter(value => value && value !== correct)
  const unique = [...new Set(pool)].slice(0, 3)
  return shuffle([correct, ...unique]).slice(0, 4)
}

const LISTENING_INFLECTION_DEFINITION_RE = /(?:复数|现在分词|过去式|过去分词|第三人称单数|\bpl\.)/i

function levenshtein(left: string, right: string): number {
  const row = Array.from({ length: right.length + 1 }, (_value, index) => index)
  for (let leftIndex = 1; leftIndex <= left.length; leftIndex += 1) {
    let previousDiagonal = row[0]
    row[0] = leftIndex
    for (let rightIndex = 1; rightIndex <= right.length; rightIndex += 1) {
      const previousValue = row[rightIndex]
      row[rightIndex] = left[leftIndex - 1] === right[rightIndex - 1]
        ? previousDiagonal
        : 1 + Math.min(previousDiagonal, row[rightIndex], row[rightIndex - 1])
      previousDiagonal = previousValue
    }
  }
  return row[right.length]
}

function normalizePhonetic(value: string | null | undefined): string {
  return String(value ?? '').replace(/[/[\]ˈˌ.: ]/g, '').toLowerCase()
}

function phoneticSimilarity(left: string | null | undefined, right: string | null | undefined): number {
  const normalizedLeft = normalizePhonetic(left)
  const normalizedRight = normalizePhonetic(right)
  if (!normalizedLeft || !normalizedRight) return 0
  return 1 - levenshtein(normalizedLeft, normalizedRight) / Math.max(normalizedLeft.length, normalizedRight.length)
}

function listeningDistractorScore(target: MobileWord, candidate: MobileWord): number {
  const targetKey = normalizeAnswer(target.word)
  const candidateKey = normalizeAnswer(candidate.word)
  if (!targetKey || !candidateKey) return 0
  const spellingSimilarity = 1 - levenshtein(targetKey, candidateKey) / Math.max(targetKey.length, candidateKey.length, 1)
  return spellingSimilarity * 5 + phoneticSimilarity(target.phonetic, candidate.phonetic) * 4
}

function isStrongListeningDistractor(target: MobileWord, candidate: MobileWord): boolean {
  const targetKey = normalizeAnswer(target.word)
  const candidateKey = normalizeAnswer(candidate.word)
  if (!targetKey || !candidateKey) return false
  const spellingSimilarity = 1 - levenshtein(targetKey, candidateKey) / Math.max(targetKey.length, candidateKey.length, 1)
  return phoneticSimilarity(target.phonetic, candidate.phonetic) >= 0.62 || spellingSimilarity >= 0.65
}

function listeningInflectionBaseKeys(word: string): string[] {
  const key = normalizeAnswer(word)
  if (!key || key.includes(' ')) return []

  const keys = new Set<string>()
  const add = (value: string) => {
    const normalized = normalizeAnswer(value)
    if (normalized && normalized !== key) keys.add(normalized)
  }

  if (key.endsWith('ies') && key.length > 4) add(`${key.slice(0, -3)}y`)
  if (key.endsWith('ves') && key.length > 4) {
    add(`${key.slice(0, -3)}f`)
    add(`${key.slice(0, -3)}fe`)
  }
  if (/(?:ches|shes|xes|zes|ses|oes)$/.test(key) && key.length > 4) add(key.slice(0, -2))
  if (key.endsWith('s') && key.length > 3 && !/(?:ss|us|is)$/.test(key)) add(key.slice(0, -1))

  if (key.endsWith('ing') && key.length > 5) {
    const stem = key.slice(0, -3)
    add(stem)
    add(`${stem}e`)
    if (stem.length > 2 && stem[stem.length - 1] === stem[stem.length - 2]) add(stem.slice(0, -1))
  }

  if (key.endsWith('ied') && key.length > 4) add(`${key.slice(0, -3)}y`)
  if (key.endsWith('ed') && key.length > 4) {
    const stem = key.slice(0, -2)
    add(stem)
    add(`${stem}e`)
    if (stem.length > 2 && stem[stem.length - 1] === stem[stem.length - 2]) add(stem.slice(0, -1))
  }

  return [...keys]
}

function isListeningInflectionCandidate(word: MobileWord, knownWordKeys: Set<string>): boolean {
  if (LISTENING_INFLECTION_DEFINITION_RE.test(word.definition ?? '')) return true
  return listeningInflectionBaseKeys(word.word).some(key => knownWordKeys.has(key))
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
