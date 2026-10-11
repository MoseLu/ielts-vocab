import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, it } from 'node:test'
import {
  buildMobileWrongWordsReviewQueue,
  buildQuickMemoryReviewQueuePath,
  buildNextErrorReviewRoundWords,
  resolvePracticeQueueSource,
  type WrongWord,
} from '@ielts-vocab/app-core'

const mobileRoot = new URL('..', import.meta.url).pathname
const workspaceRoot = join(mobileRoot, '..', '..')

function read(relativePath: string): string {
  return readFileSync(join(workspaceRoot, relativePath), 'utf8')
}

function makeWrongWord(word: string, mistakeType: string): WrongWord {
  return {
    word,
    book_id: '',
    book_title: '',
    chapter_id: null,
    chapter_title: '',
    definition: word,
    dimension_states: {},
    ebbinghaus_completed: false,
    ebbinghaus_remaining: 0,
    ebbinghaus_streak: 0,
    examples: [],
    group_key: '',
    last_error_at: '',
    listening_confusables: [],
    mistake_type: mistakeType,
    pending_dimensions: [],
    phonetic: '',
    pos: '',
    recognition_pass_streak: 0,
    wrong_count: 1,
  }
}

describe('mobile quick-memory due review contract', () => {
  it('builds the same due-review queue endpoint shape as Web practice', () => {
    assert.equal(
      buildQuickMemoryReviewQueuePath({
        bookId: 'book-a',
        chapterId: 2,
        limit: 10,
        offset: 0,
        withinDays: 3,
      }),
      '/api/ai/quick-memory/review-queue?limit=10&within_days=3&offset=0&scope=due&book_id=book-a&chapter_id=2',
    )
  })

  it('keeps due-review recognition queues distinct from chapter/book loading', () => {
    assert.equal(resolvePracticeQueueSource({ dueReviewRequested: true, mode: 'quickmemory' }), 'due-review')
    assert.equal(resolvePracticeQueueSource({ dueReviewRequested: true, mode: 'test' }), 'due-review')
    assert.equal(resolvePracticeQueueSource({ dueReviewRequested: false, mode: 'quickmemory' }), 'chapter')
  })

  it('wires PracticeScreen to the review queue without replacing normal chapter loading', () => {
    const learnerApiSource = read('apps/mobile/src/api/learnerApi.ts')
    const practiceSource = read('apps/mobile/src/screens/PracticeScreen.tsx')
    const practiceDataSource = read('apps/mobile/src/features/practice/runtime/practiceDataLoading.ts')
    const answerSubmissionSource = read('apps/mobile/src/features/practice/runtime/usePracticeAnswerSubmission.ts')

    assert.match(learnerApiSource, /export async function loadQuickMemoryReviewQueue/)
    assert.match(learnerApiSource, /buildQuickMemoryReviewQueuePath\(options\)/)
    assert.match(practiceSource, /loadPracticeQueue/)
    assert.match(practiceDataSource, /resolvePracticeQueueSource/)
    assert.match(practiceDataSource, /loadQuickMemoryReviewQueue/)
    assert.match(practiceDataSource, /loadChapterWords\(params\.bookId, params\.chapterId\)/)
    assert.match(answerSubmissionSource, /persistPracticeSessionProgress/)
    assert.match(read('apps/mobile/src/features/practice/runtime/practiceSessionLifecycle.ts'), /queueSource !== 'chapter'/)
    assert.match(practiceSource, /queueSource === 'due-review'/)
    assert.match(answerSubmissionSource, /params\.mode === 'quickmemory' \|\| params\.mode === 'test'/)
  })

  it('keeps wrong-word recovery filters and selected-word review wired on mobile', () => {
    const learnerApiSource = read('apps/mobile/src/api/learnerApi.ts')
    const errorsSource = read('apps/mobile/src/screens/ErrorsScreen.tsx')
    const practiceDataSource = read('apps/mobile/src/features/practice/runtime/practiceDataLoading.ts')
    const navigationSource = read('apps/mobile/src/navigation/types.ts')

    assert.match(learnerApiSource, /dim: filters\.dimension === 'all' \? undefined : filters\.dimension/)
    assert.match(learnerApiSource, /mode: filters\.mode === 'all' \? undefined : filters\.mode/)
    assert.match(errorsSource, /testID="errors\.practiceSelected"/)
    assert.match(errorsSource, /selectedWrongWords: selectedWordValues/)
    assert.match(errorsSource, /testID=\{`errors\.dimension\.\$\{item\.value\}`\}/)
    assert.match(errorsSource, /testID=\{`errors\.mode\.\$\{item\.value\}`\}/)
    assert.match(navigationSource, /selectedWrongWords\?: string\[\]/)
    assert.match(navigationSource, /wrongWordFilters\?: MobileWrongWordFilters/)
    assert.match(practiceDataSource, /buildMobileWrongWordsReviewQueue/)
    assert.match(practiceDataSource, /params\.options\?\.selectedWrongWords \?\? \[\]/)
  })

  it('keeps wrong-word next-round and progress persistence wired on mobile', () => {
    const practiceSource = read('apps/mobile/src/screens/PracticeScreen.tsx')
    const answerSubmissionSource = read('apps/mobile/src/features/practice/runtime/usePracticeAnswerSubmission.ts')
    const progressStorageSource = read('apps/mobile/src/features/practice/runtime/errorReviewProgressStorage.ts')

    assert.match(progressStorageSource, /CORE_STORAGE_KEYS\.wrongWordReview/)
    assert.match(progressStorageSource, /buildErrorReviewProgress/)
    assert.match(practiceSource, /hydrateErrorReviewProgress/)
    assert.match(practiceSource, /persistErrorReviewProgress/)
    assert.match(practiceSource, /buildNextErrorReviewRoundWords/)
    assert.match(practiceSource, /testID="practice\.errors\.nextRound"/)
    assert.match(answerSubmissionSource, /updateErrorReviewRoundResults/)
  })

  it('builds selected and retry wrong-word queues with app-core helpers', () => {
    const words = [
      makeWrongWord('Alpha', 'recognition'),
      makeWrongWord('Beta', 'meaning'),
    ]

    assert.deepEqual(buildMobileWrongWordsReviewQueue(words, {}, ['Beta']).map(item => item.word), ['Beta'])
    assert.deepEqual(buildNextErrorReviewRoundWords(words, { alpha: true, beta: false }).map(item => item.word), ['Beta'])
  })

  it('wires smart mode to profile-backed dimension choice and smart-stats sync', () => {
    const learnerApiSource = read('apps/mobile/src/api/learnerApi.ts')
    const smartHookSource = read('apps/mobile/src/features/practice/runtime/useMobileSmartPractice.ts')
    const practiceSource = read('apps/mobile/src/screens/PracticeScreen.tsx')
    const answerSubmissionSource = read('apps/mobile/src/features/practice/runtime/usePracticeAnswerSubmission.ts')

    assert.match(learnerApiSource, /export async function loadSmartStats/)
    assert.match(learnerApiSource, /\/api\/ai\/smart-stats/)
    assert.match(learnerApiSource, /export async function syncSmartStats/)
    assert.match(smartHookSource, /loadLearnerProfile\(\)/)
    assert.match(smartHookSource, /loadLearningStats\(\)/)
    assert.match(smartHookSource, /selectSmartPracticeDimension/)
    assert.match(smartHookSource, /recordSmartPracticeResult/)
    assert.match(smartHookSource, /mode: 'smart'/)
    assert.match(practiceSource, /resolveSmartPracticeMode\(smartDimension\)/)
    assert.match(answerSubmissionSource, /const currentSmartDimension = params\.mode === 'smart' \? params\.smartDimension : undefined/)
    assert.match(answerSubmissionSource, /evaluatePracticeAnswer\(params\.currentWord, params\.mode, value, \{ smartDimension: currentSmartDimension \}\)/)
    assert.match(answerSubmissionSource, /params\.recordSmartAnswer\(\{/)
    assert.match(answerSubmissionSource, /dimension: currentSmartDimension/)
    assert.match(answerSubmissionSource, /buildWrongWordRecord\(params\.currentWord, params\.mode, currentSmartDimension\)/)
    assert.match(answerSubmissionSource, /params\.mode === 'quickmemory' \|\| params\.mode === 'test'/)
    assert.match(practiceSource, /activeMode === 'listening'/)
  })

  it('splits mobile practice runtime into owned loading, session, and submission surfaces', () => {
    const practiceSource = read('apps/mobile/src/screens/PracticeScreen.tsx')
    const runtimeIndexSource = read('apps/mobile/src/features/practice/runtime/index.ts')
    const dataSource = read('apps/mobile/src/features/practice/runtime/practiceDataLoading.ts')
    const sessionStateSource = read('apps/mobile/src/features/practice/runtime/usePracticeSessionState.ts')
    const answerSubmissionSource = read('apps/mobile/src/features/practice/runtime/usePracticeAnswerSubmission.ts')

    assert.match(practiceSource, /usePracticeSessionState\(\)/)
    assert.match(practiceSource, /usePracticeAnswerSubmission\(/)
    assert.match(practiceSource, /loadPracticeBootstrap\(options\)/)
    assert.match(practiceSource, /from '\.\.\/features\/practice\/runtime'/)
    assert.match(runtimeIndexSource, /export \* from '\.\/practiceDataLoading'/)
    assert.match(runtimeIndexSource, /export \* from '\.\/usePracticeSessionState'/)
    assert.match(runtimeIndexSource, /export \* from '\.\/usePracticeAnswerSubmission'/)
    assert.match(dataSource, /export async function loadPracticeQueue/)
    assert.match(sessionStateSource, /export function usePracticeSessionState/)
    assert.match(answerSubmissionSource, /export function usePracticeAnswerSubmission/)
    assert.equal(practiceSource.includes('evaluatePracticeAnswer(currentWord'), false)
    assert.equal(existsSync(join(workspaceRoot, 'apps/mobile/src/screens/practiceDataLoading.ts')), false)
    assert.equal(existsSync(join(workspaceRoot, 'apps/mobile/src/screens/usePracticeSessionState.ts')), false)
    assert.equal(existsSync(join(workspaceRoot, 'apps/mobile/src/screens/usePracticeAnswerSubmission.ts')), false)
  })
})
