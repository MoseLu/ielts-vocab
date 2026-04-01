import { filterWrongWords } from './wrongWordsFilters'

describe('wrongWordsFilters', () => {
  it('filters wrong words by date range, minimum wrong count, and dimension together', () => {
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
      minWrongCount: 5,
      startDate: '2026-03-31',
      endDate: '2026-03-31',
    })

    expect(result.map(word => word.word)).toEqual(['alpha'])
  })
})
