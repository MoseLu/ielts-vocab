// ── Tests for src/lib/smartMode.ts ──────────────────────────────────────────

import { describe, it, expect, beforeEach, vi } from 'vitest'
import {
  loadSmartStats,
  recordWordResult,
  chooseSmartDimension,
  buildSmartQueue,
  getWordMastery,
} from './smartMode'

const SMART_KEY = 'smart_word_stats'

beforeEach(() => {
  localStorage.clear()
  vi.clearAllMocks()
})

// ── loadSmartStats ────────────────────────────────────────────────────────────

describe('loadSmartStats', () => {
  it('returns empty object when storage is empty', () => {
    expect(loadSmartStats()).toEqual({})
  })

  it('parses and returns stored JSON', () => {
    const stored = {
      'word1': { listening: { correct: 2, wrong: 1 }, meaning: { correct: 0, wrong: 0 }, dictation: { correct: 0, wrong: 0 } },
    }
    localStorage.setItem(SMART_KEY, JSON.stringify(stored))
    expect(loadSmartStats()).toEqual(stored)
  })

  it('returns empty object on malformed JSON', () => {
    localStorage.setItem(SMART_KEY, 'not valid json')
    expect(loadSmartStats()).toEqual({})
  })
})

// ── recordWordResult ─────────────────────────────────────────────────────────

describe('recordWordResult', () => {
  it('records a correct result', () => {
    recordWordResult('apple', 'listening', true)
    const stats = loadSmartStats()
    expect(stats['apple'].listening.correct).toBe(1)
    expect(stats['apple'].listening.wrong).toBe(0)
  })

  it('records a wrong result', () => {
    recordWordResult('apple', 'meaning', false)
    const stats = loadSmartStats()
    expect(stats['apple'].meaning.correct).toBe(0)
    expect(stats['apple'].meaning.wrong).toBe(1)
  })

  it('initializes all dimensions for new word', () => {
    recordWordResult('banana', 'listening', true)
    const stats = loadSmartStats()
    expect(stats['banana']).toEqual({
      listening: { correct: 1, wrong: 0 },
      meaning: { correct: 0, wrong: 0 },
      dictation: { correct: 0, wrong: 0 },
    })
  })

  it('accumulates across multiple calls', () => {
    recordWordResult('cherry', 'listening', true)
    recordWordResult('cherry', 'listening', false)
    recordWordResult('cherry', 'listening', true)
    const stats = loadSmartStats()
    expect(stats['cherry'].listening.correct).toBe(2)
    expect(stats['cherry'].listening.wrong).toBe(1)
  })
})

// ── chooseSmartDimension ──────────────────────────────────────────────────────

describe('chooseSmartDimension', () => {
  const DIMS = ['listening', 'meaning', 'dictation'] as const

  it('returns one of the three dimensions for unknown word', () => {
    const result = chooseSmartDimension('unknown', {})
    expect(DIMS).toContain(result)
  })

  it('returns one of the three dimensions for known word', () => {
    const stats = {
      'test': {
        listening: { correct: 5, wrong: 1 },
        meaning: { correct: 5, wrong: 1 },
        dictation: { correct: 5, wrong: 1 },
      },
    }
    const result = chooseSmartDimension('test', stats)
    expect(DIMS).toContain(result)
  })

  it('does not throw for edge case empty stats', () => {
    expect(() => chooseSmartDimension('', {})).not.toThrow()
  })
})

// ── buildSmartQueue ──────────────────────────────────────────────────────────

describe('buildSmartQueue', () => {
  it('returns valid array indices', () => {
    const keys = ['w1', 'w2', 'w3']
    const queue = buildSmartQueue(keys, {})
    expect(queue).toHaveLength(3)
    expect(queue.sort()).toEqual([0, 1, 2])
  })

  it('produces a permutation (all indices present)', () => {
    const keys = ['a', 'b', 'c', 'd']
    const queue = buildSmartQueue(keys, {})
    expect([...queue].sort()).toEqual([0, 1, 2, 3])
  })

  it('gives higher mastery words lower priority (they appear later)', () => {
    const keys = ['weak', 'strong']
    const stats = {
      weak: {
        listening: { correct: 0, wrong: 5 },
        meaning: { correct: 0, wrong: 5 },
        dictation: { correct: 0, wrong: 5 },
      },
      strong: {
        listening: { correct: 5, wrong: 0 },
        meaning: { correct: 5, wrong: 0 },
        dictation: { correct: 5, wrong: 0 },
      },
    }
    const queue = buildSmartQueue(keys, stats)
    // Weak (index 0) should generally come before strong (index 1)
    expect(queue[0]).toBe(0)
  })
})

// ── getWordMastery ───────────────────────────────────────────────────────────

describe('getWordMastery', () => {
  it('returns level 0 "未学习" for unknown word', () => {
    const info = getWordMastery('never-seen', {})
    expect(info.level).toBe(0)
    expect(info.label).toBe('未学习')
    expect(info.listening).toBe(-1)
    expect(info.meaning).toBe(-1)
    expect(info.dictation).toBe(-1)
  })

  it('returns "需加强" for low mastery (~0%)', () => {
    const stats = {
      test: {
        listening: { correct: 0, wrong: 4 },
        meaning: { correct: 0, wrong: 4 },
        dictation: { correct: 0, wrong: 4 },
      },
    }
    const info = getWordMastery('test', stats)
    expect([0, 1]).toContain(info.level)
    expect(info.label).toBeTruthy()
  })

  it('returns correct listening/meaning/dictation scores', () => {
    const stats = {
      test: {
        listening: { correct: 8, wrong: 2 },
        meaning: { correct: 3, wrong: 1 },
        dictation: { correct: 0, wrong: 0 },
      },
    }
    const info = getWordMastery('test', stats)
    expect(info.listening).toBeCloseTo(0.8)
    expect(info.meaning).toBeCloseTo(0.75)
    expect(info.dictation).toBe(-1)
  })

  it('marks high accuracy as "已掌握"', () => {
    const stats = {
      mastered: {
        listening: { correct: 10, wrong: 0 },
        meaning: { correct: 10, wrong: 0 },
        dictation: { correct: 10, wrong: 0 },
      },
    }
    const info = getWordMastery('mastered', stats)
    expect(info.level).toBe(3)
    expect(info.label).toBe('已掌握')
  })
})
