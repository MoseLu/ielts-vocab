// ── Smart Mode Adaptive Logic ─────────────────────────────────────────────────
// Tracks per-word proficiency across three dimensions:
//   音 (listening)  - 听音选义
//   意 (meaning)    - 看词选义
//   形 (dictation)  - 听写拼写
// Smart mode uses these stats to auto-weight which dimension to test next.

export type SmartDimension = 'listening' | 'meaning' | 'dictation'

export interface DimStats {
  correct: number
  wrong: number
}

export interface WordSmartStats {
  listening: DimStats
  meaning: DimStats
  dictation: DimStats
}

export type SmartWordStatsStore = Record<string, WordSmartStats>

const STORAGE_KEY = 'smart_word_stats'

export function loadSmartStats(): SmartWordStatsStore {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}')
  } catch {
    return {}
  }
}

function emptyWordStats(): WordSmartStats {
  return {
    listening: { correct: 0, wrong: 0 },
    meaning: { correct: 0, wrong: 0 },
    dictation: { correct: 0, wrong: 0 },
  }
}

// Record a result for a word in a given dimension (called from any practice mode)
export function recordWordResult(
  wordKey: string,
  dimension: SmartDimension,
  isCorrect: boolean,
): void {
  const stats = loadSmartStats()
  if (!stats[wordKey]) stats[wordKey] = emptyWordStats()
  if (isCorrect) {
    stats[wordKey][dimension].correct++
  } else {
    stats[wordKey][dimension].wrong++
  }
  localStorage.setItem(STORAGE_KEY, JSON.stringify(stats))
}

// Mastery for a single dimension: 0 = never tried, 0.5 = 50% accuracy, 1 = perfect
function dimMastery(dim: DimStats): number {
  const total = dim.correct + dim.wrong
  if (total === 0) return -1 // sentinel: untested
  return dim.correct / total
}

// Overall word mastery across all dimensions
function wordMastery(stats?: WordSmartStats): number {
  if (!stats) return 0 // never seen → treat as weakest
  const scores = [
    dimMastery(stats.listening),
    dimMastery(stats.meaning),
    dimMastery(stats.dictation),
  ].map(s => (s === -1 ? 0.5 : s)) // untested dims count as 50%
  return scores.reduce((a, b) => a + b, 0) / 3
}

// Choose which dimension to test next using weighted random selection.
// Untested dimensions have priority (treated as weak), then weakest tested dim wins.
export function chooseSmartDimension(
  wordKey: string,
  stats: SmartWordStatsStore,
): SmartDimension {
  const ws = stats[wordKey]
  const dims: SmartDimension[] = ['listening', 'meaning', 'dictation']

  if (!ws) {
    // No data at all: random selection
    return dims[Math.floor(Math.random() * dims.length)]
  }

  // Compute weakness weights:
  //   - untested dim → weight 0.6 (slightly prioritize exploring unknown)
  //   - tested dim   → weight = 1 - accuracy (0 = perfect, 1 = always wrong)
  const weights = dims.map(d => {
    const m = dimMastery(ws[d])
    if (m === -1) return 0.6 // untested
    return Math.max(0.05, 1 - m) // at least 5% chance even for mastered dims
  })

  const total = weights.reduce((a, b) => a + b, 0)
  let r = Math.random() * total
  for (let i = 0; i < dims.length; i++) {
    r -= weights[i]
    if (r <= 0) return dims[i]
  }
  return dims[0]
}

// Build a smart practice queue: weaker words come first.
// Words with no stats go first (prioritize learning new material).
export function buildSmartQueue(wordKeys: string[], stats: SmartWordStatsStore): number[] {
  const indices = Array.from({ length: wordKeys.length }, (_, i) => i)
  return indices.sort((a, b) => {
    const am = wordMastery(stats[wordKeys[a]])
    const bm = wordMastery(stats[wordKeys[b]])
    // Add small jitter so same-mastery words aren't always in the same order
    return am - bm + (Math.random() - 0.5) * 0.05
  })
}

export interface MasteryInfo {
  label: string
  level: 0 | 1 | 2 | 3 // 0=未学 1=需加强 2=熟悉中 3=已掌握
  listening: number     // 0-1 accuracy (-1 = untested)
  meaning: number
  dictation: number
}

// Get human-readable mastery info for a word
export function getWordMastery(wordKey: string, stats: SmartWordStatsStore): MasteryInfo {
  const ws = stats[wordKey]
  if (!ws) return { label: '未学习', level: 0, listening: -1, meaning: -1, dictation: -1 }

  const m = wordMastery(ws)
  const label = m >= 0.9 ? '已掌握' : m >= 0.6 ? '熟悉中' : m >= 0.3 ? '学习中' : '需加强'
  const level = m >= 0.9 ? 3 : m >= 0.6 ? 2 : m >= 0.3 ? 1 : 0

  return {
    label,
    level: level as 0 | 1 | 2 | 3,
    listening: dimMastery(ws.listening),
    meaning: dimMastery(ws.meaning),
    dictation: dimMastery(ws.dictation),
  }
}
