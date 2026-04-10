// ── Smart Mode Adaptive Logic ─────────────────────────────────────────────────

import { STORAGE_KEYS } from '../constants'
import { apiFetch } from './index'
// Tracks per-word proficiency across three dimensions:
//   音 (listening)  - 听音选义
//   意 (meaning)    - 默写模式
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
const PENDING_SYNC_KEY = 'smart_word_stats_pending'

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

// ── Backend sync helpers ──────────────────────────────────────────────────────

interface PendingSync {
  word: string
  listening: { correct: number; wrong: number }
  meaning: { correct: number; wrong: number }
  dictation: { correct: number; wrong: number }
  failedAt: string  // ISO timestamp
}

interface SmartStatsSyncContext {
  bookId?: string | null
  chapterId?: string | null
  mode?: string | null
}

function _loadPendingSync(): PendingSync[] {
  try {
    return JSON.parse(localStorage.getItem(PENDING_SYNC_KEY) || '[]')
  } catch {
    return []
  }
}

function _savePendingSync(pending: PendingSync[]): void {
  localStorage.setItem(PENDING_SYNC_KEY, JSON.stringify(pending))
}

function _mergePendingIntoStats(pending: PendingSync[], stats: SmartWordStatsStore): SmartWordStatsStore {
  const result = { ...stats }
  for (const p of pending) {
    const key = p.word.toLowerCase()
    const existing = result[key]
    if (!existing) {
      result[key] = {
        listening: { ...p.listening },
        meaning: { ...p.meaning },
        dictation: { ...p.dictation },
      }
    } else {
      // Merge, keeping max values per dimension
      result[key] = {
        listening: {
          correct: Math.max(existing.listening.correct, p.listening.correct),
          wrong: Math.max(existing.listening.wrong, p.listening.wrong),
        },
        meaning: {
          correct: Math.max(existing.meaning.correct, p.meaning.correct),
          wrong: Math.max(existing.meaning.wrong, p.meaning.wrong),
        },
        dictation: {
          correct: Math.max(existing.dictation.correct, p.dictation.correct),
          wrong: Math.max(existing.dictation.wrong, p.dictation.wrong),
        },
      }
    }
  }
  return result
}

/** Push all localStorage smart stats to the backend with retry queue.
 * Failed syncs are stored locally and retried on next sync attempt. */
export function syncSmartStatsToBackend(context?: SmartStatsSyncContext): void {
  if (!localStorage.getItem(STORAGE_KEYS.AUTH_USER)) return

  // Merge pending stats with current stats before syncing
  const pending = _loadPendingSync()
  const currentStats = loadSmartStats()
  const mergedStats = pending.length > 0 ? _mergePendingIntoStats(pending, currentStats) : currentStats
  const entries = Object.entries(mergedStats)
  if (!entries.length) return

  const payload = entries.map(([word, ws]) => ({
    word,
    listening: ws.listening,
    meaning: ws.meaning,
    dictation: ws.dictation,
  }))

  apiFetch('/api/ai/smart-stats/sync', {
    method: 'POST',
    body: JSON.stringify({
      stats: payload,
      context: {
        bookId: context?.bookId ?? undefined,
        chapterId: context?.chapterId ?? undefined,
        mode: context?.mode ?? undefined,
      },
    }),
  }).then(() => {
    // On success, clear pending queue since all data is now on server
    if (pending.length > 0) {
      localStorage.removeItem(PENDING_SYNC_KEY)
    }
  }).catch(() => {
    // On failure, add current stats to pending queue for retry
    // Deduplicate: don't re-add words that are already pending
    const existingPendingWords = new Set(pending.map(p => p.word.toLowerCase()))
    const newPending: PendingSync[] = [
      ...pending,
      ...entries
        .filter(([word]) => !existingPendingWords.has(word.toLowerCase()))
        .map(([word, ws]) => ({
          word,
          listening: { ...ws.listening },
          meaning: { ...ws.meaning },
          dictation: { ...ws.dictation },
          failedAt: new Date().toISOString(),
        })),
    ]
    // Keep max 7 days of pending entries
    const sevenDaysAgo = Date.now() - 7 * 24 * 60 * 60 * 1000
    const recentPending = newPending.filter(p => new Date(p.failedAt).getTime() > sevenDaysAgo)
    _savePendingSync(recentPending)
  })
}

/** Fetch smart stats from backend and merge into localStorage (backend wins per-dim if higher total). */
export async function loadSmartStatsFromBackend(): Promise<void> {
  if (!localStorage.getItem(STORAGE_KEYS.AUTH_USER)) return
  try {
    const data = await apiFetch<{ stats?: Array<{
      word: string
      listening: { correct: number; wrong: number }
      meaning:   { correct: number; wrong: number }
      dictation: { correct: number; wrong: number }
    }> }>('/api/ai/smart-stats')
    const serverStats = data.stats || []
    if (!serverStats.length) return
    const local = loadSmartStats()
    let changed = false
    for (const s of serverStats) {
      const key = s.word.toLowerCase()
      const existing = local[key]
      // Use server data if local has no entry, or if server has more total answers (more data)
      const serverTotal = (s.listening.correct + s.listening.wrong +
                          s.meaning.correct + s.meaning.wrong +
                          s.dictation.correct + s.dictation.wrong)
      const localTotal = existing
        ? (existing.listening.correct + existing.listening.wrong +
           existing.meaning.correct + existing.meaning.wrong +
           existing.dictation.correct + existing.dictation.wrong)
        : 0
      if (!existing || serverTotal > localTotal) {
        local[key] = {
          listening: s.listening,
          meaning:   s.meaning,
          dictation: s.dictation,
        }
        changed = true
      }
    }
    if (changed) localStorage.setItem(STORAGE_KEY, JSON.stringify(local))
  } catch {
    // Non-critical
  }
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
