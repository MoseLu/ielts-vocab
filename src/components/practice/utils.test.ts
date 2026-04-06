// ── Tests for src/components/practice/utils.ts ────────────────────────────────

import { describe, it, expect, vi, beforeEach } from 'vitest'
import {
  shuffleArray,
  countPhoneticSyllables,
  syllabifyWord,
  generateOptions,
  normalizeWordAnswer,
  playExampleAudio,
  preloadWordAudio,
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

  it('prioritizes learner weak words as distractors when a profile is provided', () => {
    const words = [
      { id: 1, word: 'affect', phonetic: '/əˈfekt/', definition: 'to influence', pos: 'v.', chapterId: 1 },
      { id: 2, word: 'apply', phonetic: '/əˈplaɪ/', definition: 'to use', pos: 'v.', chapterId: 1 },
      { id: 3, word: 'effect', phonetic: '/ɪˈfekt/', definition: 'a result', pos: 'n.', chapterId: 1 },
      { id: 4, word: 'effort', phonetic: '/ˈefət/', definition: 'hard work', pos: 'n.', chapterId: 1 },
      { id: 5, word: 'improve', phonetic: '/ɪmˈpruːv/', definition: 'to get better', pos: 'v.', chapterId: 1 },
    ]

    const { options } = generateOptions(words[0], words, {
      mode: 'meaning',
      priorityWords: [words[2], words[3]],
    })

    const optionWords = options.map(option => option.word)
    expect(optionWords).toContain('effect')
    expect(optionWords).toContain('effort')
    expect(options.every(option => option.display_mode === 'word')).toBe(true)
  })

  it('returns english-word options for meaning mode and tracks the correct word', () => {
    const words = [
      makeWord(1, 'correct def'),
      makeWord(2, 'wrong 1'),
      makeWord(3, 'wrong 2'),
      makeWord(4, 'wrong 3'),
    ]

    const { options, correctIndex } = generateOptions(words[0], words, 'meaning')

    expect(options).toHaveLength(4)
    expect(options.every(option => option.display_mode === 'word')).toBe(true)
    expect(options.map(option => option.word)).toContain('word1')
    expect(options[correctIndex].word).toBe('word1')
  })

  it('keeps real candidate definitions for listening mode without synthetic duplicates', () => {
    const words: import('./types').Word[] = [
      { word: 'ability', phonetic: '/əˈbɪləti/', definition: '能力；本领；才能', pos: 'n.' },
      { word: 'faculty', phonetic: '/ˈfækəlti/', definition: '能力；本领；才能', pos: 'n.' },
      { word: 'capability', phonetic: '/ˌkeɪpəˈbɪləti/', definition: '能力；才能；资质', pos: 'n.' },
      { word: 'liability', phonetic: '/ˌlaɪəˈbɪləti/', definition: '责任；债务；义务', pos: 'n.' },
      { word: 'facility', phonetic: '/fəˈsɪləti/', definition: '熟练；灵巧；能力', pos: 'n.' },
      { word: 'agility', phonetic: '/əˈdʒɪləti/', definition: '敏捷；灵活', pos: 'n.' },
    ]

    const { options, correctIndex } = generateOptions(words[0], words, 'listening')
    const distractorDefs = options
      .filter((_, index) => index !== correctIndex)
      .map(option => option.definition)
    const allowedDefs = new Set([
      '能力；才能；资质',
      '责任；债务；义务',
      '熟练；灵巧；能力',
      '敏捷；灵活',
    ])

    expect(new Set(options.map(option => option.definition)).size).toBe(options.length)
    expect(distractorDefs.every(definition => allowedDefs.has(definition))).toBe(true)
    expect(distractorDefs).not.toContain('能力；本领；才能')
    expect(options[correctIndex].definition).toBe('能力；本领；才能')
  })

  it('keeps only one distractor from the same english word family in listening mode', () => {
    const words: import('./types').Word[] = [
      { word: 'millimeter', phonetic: '/ˈmɪlɪˌmiːtə(r)/', definition: '毫米', pos: 'n.' },
      { word: 'kilometer', phonetic: '/ˈkɪləˌmiːtə(r)/', definition: '公里；千米', pos: 'n.' },
      { word: 'kilometre', phonetic: '/ˈkɪləˌmiːtə(r)/', definition: '公里', pos: 'n.' },
      { word: 'kilometers', phonetic: '/kɪˈlɒmɪtəz/', definition: '千米', pos: 'n.' },
      { word: 'barometer', phonetic: '/bəˈrɒmɪtə(r)/', definition: '气压计', pos: 'n.' },
      { word: 'researcher', phonetic: '/rɪˈsɜːtʃə(r)/', definition: '研究者', pos: 'n.' },
    ]

    const { options } = generateOptions(words[0], words, 'listening')
    const kilometerFamily = new Set(['kilometer', 'kilometre', 'kilometers'])
    const kilometerVariants = options
      .map(option => option.word)
      .filter((word): word is string => typeof word === 'string' && kilometerFamily.has(word))

    expect(kilometerVariants).toHaveLength(1)
    expect(options).toHaveLength(4)
  })
})

describe('normalizeWordAnswer', () => {
  it('normalizes case, whitespace, and surrounding punctuation', () => {
    expect(normalizeWordAnswer('  "Take Off!"  ')).toBe('take off')
  })

  it('normalizes curly apostrophes and dash variants', () => {
    expect(normalizeWordAnswer('rock’n’roll')).toBe("rock'n'roll")
    expect(normalizeWordAnswer('part–time')).toBe('part-time')
  })
})

describe('playWordAudio', () => {
  const createAudioResponse = (bytes: number[]) => ({
    ok: true,
    headers: new Headers({ 'X-Audio-Bytes': String(bytes.length) }),
    arrayBuffer: vi.fn().mockResolvedValue(new Uint8Array(bytes).buffer),
  })

  it('reuses prefetched word audio without issuing another fetch', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(createAudioResponse([4, 5, 6]))
      .mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ 'X-Audio-Bytes': '3' }),
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
      play = vi.fn().mockImplementation(() => {
        if (this.src.startsWith('data:audio/wav')) {
          this.onended?.()
        }
        return Promise.resolve(undefined)
      })

      constructor(src = '') {
        this.src = src
        createdAudioSources.push(src)
      }
    }

    Object.defineProperty(globalThis, 'fetch', { value: fetchMock, writable: true })
    Object.defineProperty(globalThis, 'Audio', { value: TestAudio as unknown as typeof Audio, writable: true })
    const createObjectURL = vi.fn(() => 'blob:cached-word-audio')
    const revokeObjectURL = vi.fn()
    Object.defineProperty(globalThis.URL, 'createObjectURL', { value: createObjectURL, writable: true })
    Object.defineProperty(globalThis.URL, 'revokeObjectURL', { value: revokeObjectURL, writable: true })

    await preloadWordAudio('prefetched-word')
    playWordAudio('prefetched-word', { playbackSpeed: '1', volume: '100' })
    await Promise.resolve()
    await Promise.resolve()
    await new Promise(resolve => setTimeout(resolve, 0))
    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(createdAudioSources.some(src => src.startsWith('blob:'))).toBe(true)
    stopAudio()
  })

  it('fetches the local word-audio endpoint without browser URL caching', async () => {
    const fetchMock = vi.fn().mockResolvedValue(createAudioResponse([1, 2, 3]))
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
      play = vi.fn().mockImplementation(() => {
        if (this.src.startsWith('data:audio/wav')) {
          this.onended?.()
        }
        return Promise.resolve(undefined)
      })

      constructor(src = '') {
        this.src = src
        createdAudioSources.push(src)
      }
    }

    Object.defineProperty(globalThis, 'fetch', { value: fetchMock, writable: true })
    Object.defineProperty(globalThis, 'Audio', { value: TestAudio as unknown as typeof Audio, writable: true })
    const createObjectURL = vi.fn(() => 'blob:word-audio')
    const revokeObjectURL = vi.fn()
    Object.defineProperty(globalThis.URL, 'createObjectURL', { value: createObjectURL, writable: true })
    Object.defineProperty(globalThis.URL, 'revokeObjectURL', { value: revokeObjectURL, writable: true })

    playWordAudio('global', { playbackSpeed: '1', volume: '100' })
    await Promise.resolve()
    await Promise.resolve()
    await new Promise(resolve => setTimeout(resolve, 0))
    expect(fetchMock).toHaveBeenCalledWith('/api/tts/word-audio?w=global', {
      cache: 'no-store',
      headers: { 'Cache-Control': 'no-cache' },
    })
    expect(createdAudioSources.some(src => src.includes('dict.youdao.com'))).toBe(false)
    expect(createdAudioSources.some(src => src.includes('api.dictionaryapi.dev'))).toBe(false)
    expect(createObjectURL).toHaveBeenCalled()
    expect(createdAudioSources.some(src => src.startsWith('blob:'))).toBe(true)

    stopAudio()
  })

  it('drops mismatched cached word audio and refetches a complete copy', async () => {
    let now = 1_000
    const nowSpy = vi.spyOn(Date, 'now').mockImplementation(() => now)
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(createAudioResponse([1, 2, 3]))
      .mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ 'X-Audio-Bytes': '4' }),
      })
      .mockResolvedValueOnce(createAudioResponse([7, 8, 9, 10]))

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
      play = vi.fn().mockImplementation(() => {
        if (this.src.startsWith('data:audio/wav')) this.onended?.()
        return Promise.resolve(undefined)
      })
    }

    Object.defineProperty(globalThis, 'fetch', { value: fetchMock, writable: true })
    Object.defineProperty(globalThis, 'Audio', { value: TestAudio as unknown as typeof Audio, writable: true })
    Object.defineProperty(globalThis.URL, 'createObjectURL', { value: vi.fn(() => 'blob:word-audio'), writable: true })
    Object.defineProperty(globalThis.URL, 'revokeObjectURL', { value: vi.fn(), writable: true })

    await preloadWordAudio('stale-word')
    now += 6_000
    playWordAudio('stale-word', { playbackSpeed: '1', volume: '100' })
    await Promise.resolve()
    await Promise.resolve()
    await new Promise(resolve => setTimeout(resolve, 0))
    expect(fetchMock).toHaveBeenNthCalledWith(2, '/api/tts/word-audio?w=stale-word', {
      method: 'HEAD',
      cache: 'no-store',
      headers: { 'Cache-Control': 'no-cache' },
    })
    expect(fetchMock).toHaveBeenNthCalledWith(3, '/api/tts/word-audio?w=stale-word', {
      cache: 'no-store',
      headers: { 'Cache-Control': 'no-cache' },
    })
    nowSpy.mockRestore()
    stopAudio()
  })

  it('drops mismatched cached example audio and refetches a complete copy', async () => {
    let now = 1_000
    const nowSpy = vi.spyOn(Date, 'now').mockImplementation(() => now)
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(createAudioResponse([1, 2, 3]))
      .mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ 'X-Audio-Bytes': '4' }),
      })
      .mockResolvedValueOnce(createAudioResponse([7, 8, 9, 10]))

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
      play = vi.fn().mockImplementation(() => {
        if (this.src.startsWith('data:audio/wav')) this.onended?.()
        return Promise.resolve(undefined)
      })
    }

    Object.defineProperty(globalThis, 'fetch', { value: fetchMock, writable: true })
    Object.defineProperty(globalThis, 'Audio', { value: TestAudio as unknown as typeof Audio, writable: true })
    Object.defineProperty(globalThis.URL, 'createObjectURL', { value: vi.fn(() => 'blob:example-audio'), writable: true })
    Object.defineProperty(globalThis.URL, 'revokeObjectURL', { value: vi.fn(), writable: true })

    playExampleAudio('Example sentence', 'alpha', { playbackSpeed: '1', volume: '100' })
    await Promise.resolve()
    await Promise.resolve()
    await new Promise(resolve => setTimeout(resolve, 0))
    now += 6_000
    playExampleAudio('Example sentence', 'alpha', { playbackSpeed: '1', volume: '100' })
    await Promise.resolve()
    await Promise.resolve()
    await new Promise(resolve => setTimeout(resolve, 0))

    expect(fetchMock).toHaveBeenNthCalledWith(2, '/api/tts/example-audio', {
      method: 'POST',
      cache: 'no-store',
      headers: {
        'Cache-Control': 'no-cache',
        'Content-Type': 'application/json',
        'X-Audio-Metadata-Only': '1',
      },
      body: JSON.stringify({ sentence: 'Example sentence', word: 'alpha' }),
    })
    expect(fetchMock).toHaveBeenNthCalledWith(3, '/api/tts/example-audio', {
      method: 'POST',
      cache: 'no-store',
      headers: {
        'Cache-Control': 'no-cache',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ sentence: 'Example sentence', word: 'alpha' }),
    })
    nowSpy.mockRestore()
    stopAudio()
  })
})
