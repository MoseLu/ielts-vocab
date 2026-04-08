import { useState, useEffect, useCallback } from 'react'
import { useAuth } from '../../../contexts'
import { apiFetch } from '../../../lib'
import {
  QUICK_MEMORY_MASTERY_TARGET,
  getQuickMemoryReviewProgress,
  isQuickMemoryRecordMastered,
  readQuickMemoryRecordsFromStorage,
} from '../../../lib/quickMemory'
import {
  WRONG_WORD_PENDING_REVIEW_TARGET,
  addWrongWordToList,
  clearAllWrongWordPendingFromList,
  clearWrongWordPendingFromList,
  loadWrongWords,
  mergeWrongWordLists,
  readWrongWordsFromStorage,
  type WrongWordDimension,
  type WrongWordRecord,
  writeWrongWordsToStorage,
} from '../wrongWordsStore'

export type WrongWord = WrongWordRecord

export interface UseWrongWordsOptions {
  includeDetails?: boolean
}

function decorateWrongWords(words: WrongWord[]): WrongWord[] {
  const records = readQuickMemoryRecordsFromStorage()

  return words.map(word => {
    const key = word.word.trim().toLowerCase()
    const quickMemoryRecord = key ? records[key] : undefined
    const quickMemoryProgress = quickMemoryRecord
      ? getQuickMemoryReviewProgress(quickMemoryRecord)
      : {
          streak: word.ebbinghaus_streak ?? 0,
          target: word.ebbinghaus_target ?? QUICK_MEMORY_MASTERY_TARGET,
          remaining: word.ebbinghaus_remaining ?? QUICK_MEMORY_MASTERY_TARGET,
          completed: Boolean(word.ebbinghaus_completed),
        }

    const recognitionPassStreak = quickMemoryRecord
      ? Math.max(
          word.recognition_pass_streak ?? 0,
          getQuickMemoryReviewProgress(quickMemoryRecord, WRONG_WORD_PENDING_REVIEW_TARGET).streak,
        )
      : (word.recognition_pass_streak ?? 0)

    const [decorated] = mergeWrongWordLists([{
      ...word,
      recognitionPassStreak: recognitionPassStreak,
      ebbinghaus_streak: quickMemoryProgress.streak,
      ebbinghaus_target: quickMemoryProgress.target,
      ebbinghaus_remaining: quickMemoryProgress.remaining,
      ebbinghaus_completed: quickMemoryRecord
        ? isQuickMemoryRecordMastered(quickMemoryRecord)
        : Boolean(word.ebbinghaus_completed),
    }])

    return decorated ?? {
      ...word,
      recognition_pass_streak: recognitionPassStreak,
      ebbinghaus_streak: quickMemoryProgress.streak,
      ebbinghaus_target: quickMemoryProgress.target,
      ebbinghaus_remaining: quickMemoryProgress.remaining,
      ebbinghaus_completed: quickMemoryProgress.completed,
    }
  })
}

export function useWrongWords(options: UseWrongWordsOptions = {}) {
  const { user } = useAuth()
  const { includeDetails = true } = options
  const [words, setWords] = useState<WrongWord[]>(() => decorateWrongWords(readWrongWordsFromStorage()))
  const [loading, setLoading] = useState(true)

  const fetchWords = useCallback(async () => {
    setLoading(true)
    try {
      const endpoint = includeDetails
        ? '/api/ai/wrong-words'
        : '/api/ai/wrong-words?details=compact'
      const nextWords = await loadWrongWords({
        user,
        fetchRemote: () => apiFetch<{ words?: WrongWord[] }>(endpoint),
      })
      setWords(decorateWrongWords(nextWords))
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }, [includeDetails, user])

  useEffect(() => {
    fetchWords()
  }, [fetchWords])

  const addWord = useCallback(async (word: WrongWord, dimension: WrongWordDimension = 'recognition') => {
    let nextWordsSnapshot: WrongWord[] = []

    setWords(prev => {
      const nextWords = addWrongWordToList(prev, { ...word, wrong_count: word.wrong_count ?? 1 }, { dimension })
      nextWordsSnapshot = nextWords
      writeWrongWordsToStorage(nextWords)
      return decorateWrongWords(nextWords)
    })

    if (!user) return
    try {
      const targetWord = nextWordsSnapshot.find(
        item => item.word.trim().toLowerCase() === word.word.trim().toLowerCase(),
      )
      if (!targetWord) return

      await apiFetch('/api/ai/wrong-words/sync', {
        method: 'POST',
        body: JSON.stringify({ words: [targetWord] }),
      })
    } catch {
      // ignore
    }
  }, [user])

  const removeWord = useCallback(async (word: string) => {
    let nextWordsSnapshot: WrongWord[] = []

    setWords(prev => {
      const nextWords = clearWrongWordPendingFromList(prev, word)
      nextWordsSnapshot = nextWords
      writeWrongWordsToStorage(nextWords)
      return decorateWrongWords(nextWords)
    })

    if (!user) return
    try {
      const targetWord = nextWordsSnapshot.find(
        item => item.word.trim().toLowerCase() === word.trim().toLowerCase(),
      )
      if (!targetWord) return

      await apiFetch('/api/ai/wrong-words/sync', {
        method: 'POST',
        body: JSON.stringify({ words: [targetWord] }),
      })
    } catch {
      // ignore
    }
  }, [user])

  const clearAll = useCallback(async () => {
    let nextWordsSnapshot: WrongWord[] = []

    setWords(prev => {
      const nextWords = clearAllWrongWordPendingFromList(prev)
      nextWordsSnapshot = nextWords
      writeWrongWordsToStorage(nextWords)
      return decorateWrongWords(nextWords)
    })

    if (!user) return
    try {
      await apiFetch('/api/ai/wrong-words/sync', {
        method: 'POST',
        body: JSON.stringify({ words: nextWordsSnapshot }),
      })
    } catch {
      // ignore
    }
  }, [user])

  return { words, loading, addWord, removeWord, clearAll, refetch: fetchWords }
}
