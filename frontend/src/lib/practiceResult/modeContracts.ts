import {
  CANONICAL_PRACTICE_MODES,
  type CanonicalPracticeMode,
} from '../../constants/practiceModes'

export type PracticeRuntimeId =
  | CanonicalPracticeMode
  | 'quickmemory-review'
  | 'game'
  | 'match'

export type PracticeRuntimeKind =
  | 'practice'
  | 'review-overlay'
  | 'quickmemory-review'
  | 'game-campaign'
  | 'match-book'
  | 'radio-session'

export type PracticeQueueSource =
  | 'canonical-word-list'
  | 'quick-memory-review-queue'
  | 'wrong-word-store'
  | 'game-state'
  | 'confusable-groups'

export type PracticeDimensionResolver =
  | 'smart-current-dimension'
  | 'fixed-recognition'
  | 'fixed-listening'
  | 'fixed-meaning'
  | 'fixed-dictation'
  | 'fixed-speaking'
  | 'wrong-word-target-dimension'
  | 'game-node-dimension'
  | 'match-group'
  | 'none'

export type PracticeResultPlane =
  | 'progress'
  | 'chapterModeProgress'
  | 'session'
  | 'quickMemory'
  | 'smartStats'
  | 'wordMastery'
  | 'wrongWordsOnFailure'
  | 'wrongWordsOnUnknown'
  | 'wrongWordDimensionState'
  | 'localErrorProgress'
  | 'gameState'
  | 'gameWrongWordProjection'
  | 'modePerformance'
  | 'resumeProgress'

export type PracticeProgressPolicy =
  | 'book-or-chapter-progress'
  | 'no-chapter-progress'
  | 'local-error-progress-only'
  | 'radio-resume-progress'
  | 'game-state-only'
  | 'match-chapter-progress'

export type PracticeSessionPolicy =
  | 'answer-centric-session'
  | 'quickmemory-session'
  | 'session-centric'
  | 'game-session'

export type PracticeResumePolicy =
  | 'backend-progress-with-local-cache'
  | 'quick-memory-review-page'
  | 'wrong-word-local-progress'
  | 'radio-index'
  | 'game-state'
  | 'match-progress'

export interface PracticeModeContract {
  id: PracticeRuntimeId
  runtimeKind: PracticeRuntimeKind
  route: '/practice' | '/game' | '/practice/confusable'
  queueSource: PracticeQueueSource
  dimensionResolver: PracticeDimensionResolver
  writes: readonly PracticeResultPlane[]
  progressPolicy: PracticeProgressPolicy
  sessionPolicy: PracticeSessionPolicy
  resumePolicy: PracticeResumePolicy
  answerCentric: boolean
}

const GENERIC_ANSWER_WRITES = [
  'progress',
  'session',
  'quickMemory',
  'wordMastery',
  'smartStats',
  'wrongWordsOnFailure',
  'modePerformance',
] as const

const FIXED_DIMENSION_BY_MODE = {
  listening: 'fixed-listening',
  meaning: 'fixed-meaning',
  dictation: 'fixed-dictation',
  follow: 'fixed-speaking',
} as const

const CONTRACTS = {
  smart: {
    id: 'smart',
    runtimeKind: 'practice',
    route: '/practice',
    queueSource: 'canonical-word-list',
    dimensionResolver: 'smart-current-dimension',
    writes: GENERIC_ANSWER_WRITES,
    progressPolicy: 'book-or-chapter-progress',
    sessionPolicy: 'answer-centric-session',
    resumePolicy: 'backend-progress-with-local-cache',
    answerCentric: true,
  },
  listening: {
    id: 'listening',
    runtimeKind: 'practice',
    route: '/practice',
    queueSource: 'canonical-word-list',
    dimensionResolver: FIXED_DIMENSION_BY_MODE.listening,
    writes: GENERIC_ANSWER_WRITES,
    progressPolicy: 'book-or-chapter-progress',
    sessionPolicy: 'answer-centric-session',
    resumePolicy: 'backend-progress-with-local-cache',
    answerCentric: true,
  },
  meaning: {
    id: 'meaning',
    runtimeKind: 'practice',
    route: '/practice',
    queueSource: 'canonical-word-list',
    dimensionResolver: FIXED_DIMENSION_BY_MODE.meaning,
    writes: GENERIC_ANSWER_WRITES,
    progressPolicy: 'book-or-chapter-progress',
    sessionPolicy: 'answer-centric-session',
    resumePolicy: 'backend-progress-with-local-cache',
    answerCentric: true,
  },
  dictation: {
    id: 'dictation',
    runtimeKind: 'practice',
    route: '/practice',
    queueSource: 'canonical-word-list',
    dimensionResolver: FIXED_DIMENSION_BY_MODE.dictation,
    writes: GENERIC_ANSWER_WRITES,
    progressPolicy: 'book-or-chapter-progress',
    sessionPolicy: 'answer-centric-session',
    resumePolicy: 'backend-progress-with-local-cache',
    answerCentric: true,
  },
  follow: {
    id: 'follow',
    runtimeKind: 'practice',
    route: '/practice',
    queueSource: 'canonical-word-list',
    dimensionResolver: FIXED_DIMENSION_BY_MODE.follow,
    writes: GENERIC_ANSWER_WRITES.filter(plane => plane !== 'smartStats'),
    progressPolicy: 'book-or-chapter-progress',
    sessionPolicy: 'answer-centric-session',
    resumePolicy: 'backend-progress-with-local-cache',
    answerCentric: true,
  },
  radio: {
    id: 'radio',
    runtimeKind: 'radio-session',
    route: '/practice',
    queueSource: 'canonical-word-list',
    dimensionResolver: 'none',
    writes: ['session', 'resumeProgress'],
    progressPolicy: 'radio-resume-progress',
    sessionPolicy: 'session-centric',
    resumePolicy: 'radio-index',
    answerCentric: false,
  },
  quickmemory: {
    id: 'quickmemory',
    runtimeKind: 'practice',
    route: '/practice',
    queueSource: 'canonical-word-list',
    dimensionResolver: 'fixed-recognition',
    writes: ['quickMemory', 'session', 'progress', 'chapterModeProgress', 'wrongWordsOnUnknown', 'wordMastery'],
    progressPolicy: 'book-or-chapter-progress',
    sessionPolicy: 'quickmemory-session',
    resumePolicy: 'backend-progress-with-local-cache',
    answerCentric: true,
  },
  test: {
    id: 'test',
    runtimeKind: 'practice',
    route: '/practice',
    queueSource: 'canonical-word-list',
    dimensionResolver: 'fixed-recognition',
    writes: ['quickMemory', 'session', 'progress', 'chapterModeProgress', 'wrongWordsOnUnknown', 'wordMastery'],
    progressPolicy: 'book-or-chapter-progress',
    sessionPolicy: 'quickmemory-session',
    resumePolicy: 'backend-progress-with-local-cache',
    answerCentric: true,
  },
  errors: {
    id: 'errors',
    runtimeKind: 'review-overlay',
    route: '/practice',
    queueSource: 'wrong-word-store',
    dimensionResolver: 'wrong-word-target-dimension',
    writes: ['wrongWordDimensionState', 'quickMemory', 'wordMastery', 'session', 'localErrorProgress', 'modePerformance'],
    progressPolicy: 'local-error-progress-only',
    sessionPolicy: 'answer-centric-session',
    resumePolicy: 'wrong-word-local-progress',
    answerCentric: true,
  },
  'quickmemory-review': {
    id: 'quickmemory-review',
    runtimeKind: 'quickmemory-review',
    route: '/practice',
    queueSource: 'quick-memory-review-queue',
    dimensionResolver: 'fixed-recognition',
    writes: ['quickMemory', 'session', 'wrongWordsOnUnknown', 'wordMastery'],
    progressPolicy: 'no-chapter-progress',
    sessionPolicy: 'quickmemory-session',
    resumePolicy: 'quick-memory-review-page',
    answerCentric: true,
  },
  game: {
    id: 'game',
    runtimeKind: 'game-campaign',
    route: '/game',
    queueSource: 'game-state',
    dimensionResolver: 'game-node-dimension',
    writes: ['gameState', 'wordMastery', 'gameWrongWordProjection'],
    progressPolicy: 'game-state-only',
    sessionPolicy: 'game-session',
    resumePolicy: 'game-state',
    answerCentric: true,
  },
  match: {
    id: 'match',
    runtimeKind: 'match-book',
    route: '/practice/confusable',
    queueSource: 'confusable-groups',
    dimensionResolver: 'match-group',
    writes: ['progress', 'chapterModeProgress'],
    progressPolicy: 'match-chapter-progress',
    sessionPolicy: 'game-session',
    resumePolicy: 'match-progress',
    answerCentric: false,
  },
} as const satisfies Record<PracticeRuntimeId, PracticeModeContract>

export const PRACTICE_MODE_CONTRACTS = CONTRACTS

export const PRACTICE_RUNTIME_IDS = Object.keys(CONTRACTS) as PracticeRuntimeId[]

export function getPracticeModeContract(id: PracticeRuntimeId): PracticeModeContract {
  return CONTRACTS[id]
}

export function isPracticeRuntimeId(value: string | null | undefined): value is PracticeRuntimeId {
  return Boolean(value && value in CONTRACTS)
}

export function isAnswerCentricRuntime(id: PracticeRuntimeId): boolean {
  return CONTRACTS[id].answerCentric
}

export interface ResolvePracticeRuntimeInput {
  route: string
  mode?: string | null
  review?: string | null
  bookPracticeMode?: string | null
}

export function resolvePracticeRuntimeId(input: ResolvePracticeRuntimeInput): PracticeRuntimeId {
  const route = input.route.replace(/\/+$/, '') || '/'
  const mode = input.mode?.trim().toLowerCase() || ''
  const review = input.review?.trim().toLowerCase() || ''
  const bookPracticeMode = input.bookPracticeMode?.trim().toLowerCase() || ''

  if (route.startsWith('/game') || mode === 'game') return 'game'
  if (route === '/practice/confusable' || bookPracticeMode === 'match') return 'match'
  if (route === '/errors' || mode === 'errors') return 'errors'
  if (route === '/practice' && review === 'due') return 'quickmemory-review'
  if (isPracticeRuntimeId(mode)) return mode
  return 'smart'
}

export function resolvePracticeModeContract(input: ResolvePracticeRuntimeInput): PracticeModeContract {
  return getPracticeModeContract(resolvePracticeRuntimeId(input))
}

export function getCanonicalModeContractIds(): CanonicalPracticeMode[] {
  return CANONICAL_PRACTICE_MODES.filter(mode => mode in CONTRACTS)
}
