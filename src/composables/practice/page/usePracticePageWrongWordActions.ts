import { useCallback, type MutableRefObject } from 'react'
import {
  addWrongWordToList,
  applyWrongWordReviewResult,
  isWrongWordPendingInDimension,
  readWrongWordsFromStorage,
  syncWrongWordDimensionPassStreak,
  writeWrongWordsToStorage,
  WRONG_WORD_DIMENSION_LABELS,
} from '../../../features/vocabulary/wrongWordsStore'
import { apiFetch } from '../../../lib'
import { loadSmartStats } from '../../../lib/smartMode'
import { updateErrorReviewRoundResults, type ErrorReviewRoundResults } from '../../../components/practice/errorReviewSession'
import { resolveWrongWordDimensionForPractice } from '../../../components/practice/page/practicePageHelpers'
import type { QuickMemoryRecordState, SmartDimension, PracticeMode, Word } from '../../../components/practice/types'

interface UsePracticePageWrongWordActionsParams {
  user: unknown
  userId: string | number | null
  mode?: PracticeMode
  smartDimension: SmartDimension
  bookId: string | null
  chapterId: string | null
  errorMode: boolean
  showToast?: (message: string, type?: 'success' | 'error' | 'info') => void
  errorRoundResultsRef: MutableRefObject<ErrorReviewRoundResults>
}

export function usePracticePageWrongWordActions({
  user,
  userId,
  mode,
  smartDimension,
  bookId,
  chapterId,
  errorMode,
  showToast,
  errorRoundResultsRef,
}: UsePracticePageWrongWordActionsParams) {
  const saveWrongWord = useCallback((word: Word) => {
    const dimension = resolveWrongWordDimensionForPractice(mode, smartDimension)
    const nextWords = addWrongWordToList(
      readWrongWordsFromStorage(userId),
      word,
      { dimension },
    )
    writeWrongWordsToStorage(nextWords, userId)

    const smartStats = loadSmartStats()[word.word]
    const syncedWord = nextWords.find(
      item => item.word.trim().toLowerCase() === word.word.trim().toLowerCase(),
    )
    if (!syncedWord) return

    apiFetch('/api/ai/wrong-words/sync', {
      method: 'POST',
      body: JSON.stringify({
        sourceMode: mode,
        bookId: bookId ?? undefined,
        chapterId: chapterId ?? undefined,
        words: [{
          ...syncedWord,
          listeningCorrect: smartStats?.listening.correct ?? syncedWord.listening_correct ?? 0,
          listeningWrong: smartStats?.listening.wrong ?? syncedWord.listening_wrong ?? 0,
          meaningCorrect: smartStats?.meaning.correct ?? syncedWord.meaning_correct ?? 0,
          meaningWrong: smartStats?.meaning.wrong ?? syncedWord.meaning_wrong ?? 0,
          dictationCorrect: smartStats?.dictation.correct ?? syncedWord.dictation_correct ?? 0,
          dictationWrong: smartStats?.dictation.wrong ?? syncedWord.dictation_wrong ?? 0,
        }],
      }),
    }).catch(() => {})
  }, [bookId, chapterId, mode, smartDimension, userId])

  const handleQuickMemoryRecordChange = useCallback((word: Word, record: QuickMemoryRecordState) => {
    const currentWrongWords = readWrongWordsFromStorage(userId)
    const previousWrongWord = currentWrongWords.find(
      item => item.word.trim().toLowerCase() === word.word.trim().toLowerCase(),
    )
    if (!previousWrongWord) return

    const reviewResult = applyWrongWordReviewResult(
      currentWrongWords,
      word.word,
      record.status === 'known',
      'recognition',
    )
    const nextWords = record.status === 'known'
      ? syncWrongWordDimensionPassStreak(
          reviewResult.words,
          word.word,
          'recognition',
          record.knownCount,
        )
      : reviewResult.words
    writeWrongWordsToStorage(nextWords, userId)

    const nextWrongWord = nextWords.find(
      item => item.word.trim().toLowerCase() === word.word.trim().toLowerCase(),
    )
    const recognitionCleared = isWrongWordPendingInDimension(previousWrongWord, 'recognition')
      && !isWrongWordPendingInDimension(nextWrongWord ?? {}, 'recognition')

    if (user && nextWrongWord) {
      apiFetch('/api/ai/wrong-words/sync', {
        method: 'POST',
        body: JSON.stringify({
          sourceMode: 'quickmemory',
          bookId: bookId ?? undefined,
          chapterId: chapterId ?? undefined,
          words: [nextWrongWord],
        }),
      }).catch(() => {})
    }

    if (recognitionCleared) {
      showToast?.(`${word.word} 的「${WRONG_WORD_DIMENSION_LABELS.recognition}」已移出未过错词`, 'success')
    }
  }, [bookId, chapterId, showToast, user, userId])

  const recordErrorReviewOutcome = useCallback((word: Word, wasCorrect: boolean) => {
    if (!errorMode) return

    const reviewDimension = resolveWrongWordDimensionForPractice(mode, smartDimension)
    errorRoundResultsRef.current = updateErrorReviewRoundResults(
      errorRoundResultsRef.current,
      word.word,
      wasCorrect,
    )

    const currentWrongWords = readWrongWordsFromStorage(userId)
    const previousWrongWord = currentWrongWords.find(
      item => item.word.trim().toLowerCase() === word.word.trim().toLowerCase(),
    )
    const result = applyWrongWordReviewResult(
      currentWrongWords,
      word.word,
      wasCorrect,
      reviewDimension,
    )
    writeWrongWordsToStorage(result.words, userId)

    const nextWrongWord = result.words.find(
      item => item.word.trim().toLowerCase() === word.word.trim().toLowerCase(),
    )
    const dimensionCleared = previousWrongWord
      ? isWrongWordPendingInDimension(previousWrongWord, reviewDimension)
        && (!nextWrongWord || !isWrongWordPendingInDimension(nextWrongWord, reviewDimension))
      : false

    if (user && nextWrongWord) {
      apiFetch('/api/ai/wrong-words/sync', {
        method: 'POST',
        body: JSON.stringify({
          sourceMode: mode,
          bookId: bookId ?? undefined,
          chapterId: chapterId ?? undefined,
          words: [nextWrongWord],
        }),
      }).catch(() => {})
    }

    if (wasCorrect && dimensionCleared) {
      showToast?.(`${word.word} 的「${WRONG_WORD_DIMENSION_LABELS[reviewDimension]}」已移出未过错词`, 'success')
    }
  }, [bookId, chapterId, errorMode, mode, showToast, smartDimension, user, userId, errorRoundResultsRef])

  return {
    saveWrongWord,
    handleQuickMemoryRecordChange,
    recordErrorReviewOutcome,
  }
}
