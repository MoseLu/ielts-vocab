import { describe, expect, it } from 'vitest'
import { CANONICAL_PRACTICE_MODES } from '../../constants/practiceModes'
import {
  getCanonicalModeContractIds,
  getPracticeModeContract,
  isAnswerCentricRuntime,
  PRACTICE_RUNTIME_IDS,
  resolvePracticeModeContract,
  resolvePracticeRuntimeId,
} from './modeContracts'

describe('practice result mode contracts', () => {
  it('covers every canonical practice mode plus game and match runtimes', () => {
    expect(getCanonicalModeContractIds()).toEqual(CANONICAL_PRACTICE_MODES)
    expect(PRACTICE_RUNTIME_IDS).toEqual(expect.arrayContaining([
      'smart',
      'listening',
      'meaning',
      'dictation',
      'follow',
      'radio',
      'quickmemory',
      'errors',
      'quickmemory-review',
      'game',
      'match',
    ]))
  })

  it('declares normal answer-centric practice writes', () => {
    const smart = getPracticeModeContract('smart')

    expect(smart).toMatchObject({
      runtimeKind: 'practice',
      queueSource: 'canonical-word-list',
      dimensionResolver: 'smart-current-dimension',
      progressPolicy: 'book-or-chapter-progress',
      sessionPolicy: 'answer-centric-session',
      answerCentric: true,
    })
    expect(smart.writes).toEqual(expect.arrayContaining([
      'progress',
      'session',
      'wordMastery',
      'smartStats',
      'wrongWordsOnFailure',
    ]))
  })

  it('keeps follow answer-centric without smart stats writes', () => {
    const follow = getPracticeModeContract('follow')

    expect(follow.dimensionResolver).toBe('fixed-speaking')
    expect(follow.answerCentric).toBe(true)
    expect(follow.writes).toEqual(expect.arrayContaining([
      'progress',
      'session',
      'wordMastery',
      'wrongWordsOnFailure',
    ]))
    expect(follow.writes).not.toContain('smartStats')
  })

  it('distinguishes chapter quick memory from due review', () => {
    const chapter = getPracticeModeContract('quickmemory')
    const dueReview = getPracticeModeContract('quickmemory-review')

    expect(chapter.writes).toEqual(expect.arrayContaining([
      'quickMemory',
      'progress',
      'chapterModeProgress',
      'wrongWordsOnUnknown',
      'wordMastery',
    ]))
    expect(chapter.progressPolicy).toBe('book-or-chapter-progress')
    expect(dueReview.queueSource).toBe('quick-memory-review-queue')
    expect(dueReview.progressPolicy).toBe('no-chapter-progress')
    expect(dueReview.writes).not.toContain('progress')
    expect(dueReview.writes).not.toContain('chapterModeProgress')
  })

  it('keeps errors as a review overlay with local progress only', () => {
    const errors = getPracticeModeContract('errors')

    expect(errors.runtimeKind).toBe('review-overlay')
    expect(errors.queueSource).toBe('wrong-word-store')
    expect(errors.dimensionResolver).toBe('wrong-word-target-dimension')
    expect(errors.progressPolicy).toBe('local-error-progress-only')
    expect(errors.writes).toEqual(expect.arrayContaining([
      'wrongWordDimensionState',
      'wordMastery',
      'session',
      'localErrorProgress',
    ]))
    expect(errors.writes).not.toContain('progress')
    expect(errors.writes).not.toContain('chapterModeProgress')
  })

  it('marks radio and match as non answer-centric runtimes', () => {
    expect(isAnswerCentricRuntime('radio')).toBe(false)
    expect(isAnswerCentricRuntime('match')).toBe(false)
    expect(getPracticeModeContract('radio')).toMatchObject({
      runtimeKind: 'radio-session',
      progressPolicy: 'radio-resume-progress',
      sessionPolicy: 'session-centric',
    })
    expect(getPracticeModeContract('match')).toMatchObject({
      runtimeKind: 'match-book',
      queueSource: 'confusable-groups',
      progressPolicy: 'match-chapter-progress',
    })
  })

  it('resolves visible routes to exactly one runtime contract', () => {
    expect(resolvePracticeRuntimeId({ route: '/practice', mode: 'meaning' })).toBe('meaning')
    expect(resolvePracticeRuntimeId({ route: '/practice', review: 'due' })).toBe('quickmemory-review')
    expect(resolvePracticeRuntimeId({ route: '/practice', mode: 'errors' })).toBe('errors')
    expect(resolvePracticeRuntimeId({ route: '/practice', mode: 'game' })).toBe('game')
    expect(resolvePracticeRuntimeId({ route: '/game', mode: 'meaning' })).toBe('game')
    expect(resolvePracticeRuntimeId({ route: '/practice/confusable' })).toBe('match')
    expect(resolvePracticeRuntimeId({ route: '/practice', bookPracticeMode: 'match' })).toBe('match')
  })

  it('falls back unknown practice modes to smart', () => {
    expect(resolvePracticeModeContract({ route: '/practice', mode: 'unknown-mode' })).toMatchObject({
      id: 'smart',
      runtimeKind: 'practice',
    })
  })
})
