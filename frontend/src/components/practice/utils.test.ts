// ── Tests for src/components/practice/utils.ts ────────────────────────────────

import { describe, it, expect, vi, beforeEach } from 'vitest'
import {
  shuffleArray,
  countPhoneticSyllables,
  syllabifyWord,
  generateOptions,
  normalizeWordAnswer,
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
