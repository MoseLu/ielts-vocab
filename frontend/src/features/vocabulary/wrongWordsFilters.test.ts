import { filterWrongWords, matchesWrongWordSearchTerm } from './wrongWordsFilters'

describe('wrongWordsFilters', () => {
  it('filters wrong words by date range, wrong-count range, and dimension together', () => {
    const words = [
      {
        word: 'alpha',
        phonetic: '/a/',
        pos: 'n.',
        definition: 'alpha definition',
        wrong_count: 6,
        first_wrong_at: '2026-03-31T02:00:00.000Z',
        meaning_wrong: 3,
      },
      {
        word: 'beta',
        phonetic: '/b/',
        pos: 'n.',
        definition: 'beta definition',
        wrong_count: 4,
        first_wrong_at: '2026-03-31T04:00:00.000Z',
        meaning_wrong: 2,
      },
      {
        word: 'gamma',
        phonetic: '/g/',
        pos: 'n.',
        definition: 'gamma definition',
        wrong_count: 7,
        first_wrong_at: '2026-03-29T04:00:00.000Z',
        meaning_wrong: 2,
      },
      {
        word: 'delta',
        phonetic: '/d/',
        pos: 'n.',
        definition: 'delta definition',
        wrong_count: 8,
        first_wrong_at: '2026-03-31T05:00:00.000Z',
        listening_wrong: 3,
      },
    ]

    const result = filterWrongWords(words, {
      dimFilter: 'meaning',
      minWrongCount: 6,
      maxWrongCount: 10,
      startDate: '2026-03-31',
      endDate: '2026-03-31',
    })

    expect(result.map(word => word.word)).toEqual(['alpha'])
  })

  it('treats 11~20 and 20次以上 as non-overlapping ranges', () => {
    const words = [
      { word: 'twenty', wrong_count: 20 },
      { word: 'twenty-one', wrong_count: 21 },
    ]

    expect(filterWrongWords(words, {
      minWrongCount: 11,
      maxWrongCount: 20,
    }).map(word => word.word)).toEqual(['twenty'])

    expect(filterWrongWords(words, {
      minWrongCount: 21,
    }).map(word => word.word)).toEqual(['twenty-one'])
  })

  it('matches wrong-word search terms against the word field only', () => {
    expect(matchesWrongWordSearchTerm({
      word: 'present',
      phonetic: '/ˈprez(ə)nt/',
      pos: 'adj.',
      definition: 'current',
    }, 'pre')).toBe(true)

    expect(matchesWrongWordSearchTerm({
      word: 'without',
      phonetic: '/wɪˈðaʊt/',
      pos: 'prep.',
      definition: 'not having',
    }, 'pre')).toBe(false)

    expect(matchesWrongWordSearchTerm({
      word: 'along',
      phonetic: '/əˈlɒŋ/',
      pos: 'adv.',
      definition: 'prep. example',
    }, 'pre')).toBe(false)
  })
})
