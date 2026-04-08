import { describe, expect, it } from 'vitest'
import { buildGuidedStudySummary } from './guidedStudy'

describe('buildGuidedStudySummary', () => {
  const books = [
    { id: 'book-1', title: '核心词汇', word_count: 100 },
    { id: 'book-2', title: '阅读高频', word_count: 80 },
  ]

  it('prioritizes due review ahead of error review and new words', () => {
    const summary = buildGuidedStudySummary({
      books,
      myBookIds: new Set(['book-1']),
      progressMap: {
        'book-1': { book_id: 'book-1', current_index: 40 },
      },
      wrongWords: [
        {
          word: 'abandon',
          phonetic: '/əˈbændən/',
          pos: 'v.',
          definition: '放弃',
          meaning_wrong: 2,
          meaning_pass_streak: 0,
        },
      ],
      learnerProfile: {
        date: '2026-04-03',
        summary: {
          date: '2026-04-03',
          today_words: 0,
          today_accuracy: 0,
          today_duration_seconds: 0,
          today_sessions: 0,
          streak_days: 5,
          weakest_mode: 'meaning',
          weakest_mode_label: '默写模式',
          weakest_mode_accuracy: 62,
          due_reviews: 6,
          trend_direction: 'stable',
        },
        dimensions: [],
        focus_words: [],
        repeated_topics: [],
        next_actions: ['先复习到期词'],
        mode_breakdown: [],
      },
    })

    expect(summary.primaryAction.kind).toBe('due-review')
    expect(summary.primaryAction.ctaLabel).toBe('开始到期复习')
    expect(summary.steps[0].status).toBe('current')
    expect(summary.steps[1].status).toBe('ready')
    expect(summary.steps[2].status).toBe('ready')
  })

  it('falls back to adding a book when the user has no study plan yet', () => {
    const summary = buildGuidedStudySummary({
      books,
      myBookIds: new Set(),
      progressMap: {},
      wrongWords: [],
    })

    expect(summary.primaryAction.kind).toBe('add-book')
    expect(summary.steps[2].action.kind).toBe('add-book')
    expect(summary.steps[2].status).toBe('current')
  })

  it('recommends the strongest pending wrong-word dimension when no due review exists', () => {
    const summary = buildGuidedStudySummary({
      books,
      myBookIds: new Set(['book-1']),
      progressMap: {
        'book-1': { book_id: 'book-1', current_index: 20 },
      },
      wrongWords: [
        {
          word: 'abandon',
          phonetic: '/əˈbændən/',
          pos: 'v.',
          definition: '放弃',
          listening_wrong: 3,
          listening_pass_streak: 0,
        },
        {
          word: 'abstract',
          phonetic: '/ˈæbstrækt/',
          pos: 'adj.',
          definition: '抽象的',
          listening_wrong: 2,
          listening_pass_streak: 0,
        },
        {
          word: 'access',
          phonetic: '/ˈækses/',
          pos: 'n.',
          definition: '进入',
          meaning_wrong: 2,
          meaning_pass_streak: 0,
        },
      ],
      learnerProfile: {
        date: '2026-04-03',
        summary: {
          date: '2026-04-03',
          today_words: 0,
          today_accuracy: 0,
          today_duration_seconds: 0,
          today_sessions: 0,
          streak_days: 3,
          weakest_mode: 'listening',
          weakest_mode_label: '听音选义',
          weakest_mode_accuracy: 55,
          due_reviews: 0,
          trend_direction: 'stable',
        },
        dimensions: [],
        focus_words: [],
        repeated_topics: [],
        next_actions: [],
        mode_breakdown: [],
      },
    })

    expect(summary.primaryAction.kind).toBe('error-review')
    expect(summary.recommendedWrongDimension).toBe('listening')
    expect(summary.recommendedWrongDimensionCount).toBe(2)
  })
})
