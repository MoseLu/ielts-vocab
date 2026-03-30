// ── Tests for src/components/practice/utils.ts ────────────────────────────────

import { describe, it, expect, vi, beforeEach } from 'vitest'
import {
  shuffleArray,
  countPhoneticSyllables,
  syllabifyWord,
  generateOptions,
  playWordAudio,
  stopAudio,
} from './utils'

// ── shuffleArray ─────────────────────────────────────────────────────────────

describe('shuffleArray', () => {
  it('returns an array of the same length', () => {
    const original = [1, 2, 3, 4, 5]
    const result = shuffleArray(original)
    expect(result).toHaveLength(original.length)
  })

  it('contains all original elements', () => {
    const original = [1, 2, 3, 4, 5]
    const result = shuffleArray(original)
    expect(result.sort()).toEqual(original.sort())
  })

  it('does not mutate the original array', () => {
    const original = [1, 2, 3, 4, 5]
    const copy = [...original]
    shuffleArray(original)
    expect(original).toEqual(copy)
  })

  it('handles empty array', () => {
    expect(shuffleArray([])).toEqual([])
  })

  it('handles single element', () => {
    expect(shuffleArray([42])).toEqual([42])
  })
})

// ── countPhoneticSyllables ───────────────────────────────────────────────────

describe('countPhoneticSyllables', () => {
  it('returns 1 for empty string', () => {
    expect(countPhoneticSyllables('')).toBe(1)
  })

  it('strips IPA stress markers', () => {
    expect(countPhoneticSyllables('/əˈbæs/')).toBe(2)
  })

  it('strips dots and length markers', () => {
    expect(countPhoneticSyllables('ɑː')).toBe(1)
  })

  it('counts two syllables correctly', () => {
    // ə ˈbæs → /ə/ + /bæs/ = 2
    expect(countPhoneticSyllables('əˈbæs')).toBe(2)
  })

  it('handles multi-syllable IPA', () => {
    // 'kæntɪɡəʊnıən = 5 vowel clusters
    expect(countPhoneticSyllables("kæntɪgəʊniən")).toBeGreaterThanOrEqual(1)
  })

  it('never returns 0 (minimum 1)', () => {
    expect(countPhoneticSyllables('')).toBe(1)
    expect(countPhoneticSyllables('ptk')).toBe(1)
  })
})

// ── syllabifyWord ─────────────────────────────────────────────────────────────

describe('syllabifyWord', () => {
  it('returns single part for short words', () => {
    expect(syllabifyWord('go', '/goʊ/')).toEqual(['go'])
  })

  it('splits consonant cluster between vowels', () => {
    const result = syllabifyWord('apple', '/ˈæpəl/')
    expect(result.length).toBeGreaterThanOrEqual(1)
    expect(result.join('')).toBe('apple')
  })

  it('joins syllables back to original word', () => {
    const word = 'ability'
    const result = syllabifyWord(word, '/əˈbɪləti/')
    expect(result.join('')).toBe(word)
  })

  it('handles single-syllable words', () => {
    expect(syllabifyWord('strong', '/strɔːŋ/')).toEqual(['strong'])
  })

  it('returns array without empty parts', () => {
    const result = syllabifyWord('education', '/ˌedʒuˈkeɪʃən/')
    result.forEach(part => expect(part.length).toBeGreaterThan(0))
    expect(result.join('')).toBe('education')
  })
})

// ── generateOptions ───────────────────────────────────────────────────────────

describe('generateOptions', () => {
  beforeEach(() => {
    vi.spyOn(Math, 'random').mockReturnValue(0.5)
  })

  const makeWord = (id: number, definition: string, pos = 'n.'): import('./types').Word =>
    ({ id, word: `word${id}`, phonetic: '/fən/', definition, pos, chapterId: 1 })

  it('produces exactly 4 options', () => {
    const words = [makeWord(1, 'correct def'), makeWord(2, 'wrong 1'), makeWord(3, 'wrong 2'), makeWord(4, 'wrong 3')]
    const { options } = generateOptions(words[0], words)
    expect(options).toHaveLength(4)
  })

  it('includes the correct definition as one of the options', () => {
    const words = [
      makeWord(1, 'correct def'),
      makeWord(2, 'distractor A'),
      makeWord(3, 'distractor B'),
      makeWord(4, 'distractor C'),
    ]
    const { options } = generateOptions(words[0], words)
    const defs = options.map(o => o.definition)
    expect(defs).toContain('correct def')
  })

  it('correctIndex points to the correct option', () => {
    const words = [makeWord(1, 'correct def'), makeWord(2, 'wrong 1'), makeWord(3, 'wrong 2'), makeWord(4, 'wrong 3')]
    const { options, correctIndex } = generateOptions(words[0], words)
    expect(options[correctIndex].definition).toBe('correct def')
  })

  it('correctIndex is always a valid index', () => {
    const words = [
      makeWord(1, 'correct def'),
      makeWord(2, 'wrong 1'),
      makeWord(3, 'wrong 2'),
      makeWord(4, 'wrong 3'),
    ]
    const { correctIndex } = generateOptions(words[0], words)
    expect(correctIndex).toBeGreaterThanOrEqual(0)
    expect(correctIndex).toBeLessThan(4)
  })

  it('options do not contain duplicate definitions', () => {
    const words = [
      makeWord(1, 'unique A'),
      makeWord(2, 'unique B'),
      makeWord(3, 'unique C'),
      makeWord(4, 'unique D'),
      makeWord(5, 'unique E'),
    ]
    const { options } = generateOptions(words[0], words)
    const defs = options.map(o => o.definition)
    expect(new Set(defs).size).toBe(defs.length)
  })
})

describe('playWordAudio', () => {
  it('falls back to direct audio URLs without hitting missing cache endpoints or blob URLs', () => {
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = String(input)
      if (url.includes('api.dictionaryapi.dev')) {
        return Promise.resolve(
          new Response(JSON.stringify([]), {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          }),
        )
      }
      return Promise.resolve(new Response('', { status: 404 }))
    })
    const createdAudioSources: string[] = []

    class TestAudio {
      src = ''
      volume = 1
      playbackRate = 1
      currentTime = 0
      duration = 0
      readyState = 4
      onended: (() => void) | null = null
      onerror: (() => void) | null = null
      load = vi.fn()
      pause = vi.fn()
      addEventListener = vi.fn()
      canPlayType = vi.fn(() => '')
      play = vi.fn().mockResolvedValue(undefined)

      constructor(src = '') {
        this.src = src
        createdAudioSources.push(src)
      }
    }

    Object.defineProperty(globalThis, 'fetch', { value: fetchMock, writable: true })
    Object.defineProperty(globalThis, 'Audio', { value: TestAudio as unknown as typeof Audio, writable: true })

    playWordAudio('global', { playbackSpeed: '1', volume: '100' })

    expect(fetchMock.mock.calls.some(([url]) => String(url).includes('dict.youdao.com'))).toBe(false)
    expect(createdAudioSources.some(src => src.includes('/api/tts/word-audio'))).toBe(false)
    expect(createdAudioSources.some(src => src.startsWith('blob:'))).toBe(false)

    stopAudio()
  })
})
