import { useState, useEffect, useCallback } from 'react'
import { useAuth } from '../../../contexts'
import { apiFetch } from '../../../lib'
import {
  addWrongWordToList,
  loadWrongWords,
  removeWrongWordFromList,
  writeWrongWordsToStorage,
} from '../wrongWordsStore'

export interface WrongWord {
  word: string
  phonetic: string
  pos?: string
  definition: string
  wrong_count?: number
  // Per-dimension stats from backend
  listening_correct?: number
  listening_wrong?: number
  meaning_correct?: number
  meaning_wrong?: number
  dictation_correct?: number
  dictation_wrong?: number
}

export function useWrongWords() {
  const { user } = useAuth()
  const [words, setWords] = useState<WrongWord[]>([])
  const [loading, setLoading] = useState(true)

  const fetchWords = useCallback(async () => {
    try {
      const nextWords = await loadWrongWords({
        user,
        fetchRemote: () => apiFetch<{ words?: WrongWord[] }>('/api/ai/wrong-words'),
      })
      setWords(nextWords)
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }, [user])

  useEffect(() => {
    fetchWords()
  }, [fetchWords])

  const addWord = useCallback(async (word: WrongWord) => {
    // Optimistic update
    setWords(prev => {
      const nextWords = addWrongWordToList(prev, { ...word, wrong_count: word.wrong_count ?? 1 })
      writeWrongWordsToStorage(nextWords)
      return nextWords
    })
    if (!user) return
    try {
      await apiFetch('/api/ai/wrong-words/sync', {
        method: 'POST',
        body: JSON.stringify({ words: [word] }),
      })
    } catch {
      // ignore
    }
  }, [user])

  const removeWord = useCallback(async (word: string) => {
    setWords(prev => {
      const nextWords = removeWrongWordFromList(prev, word)
      writeWrongWordsToStorage(nextWords)
      return nextWords
    })
    if (!user) return
    try {
      await apiFetch(`/api/ai/wrong-words/${encodeURIComponent(word)}`, { method: 'DELETE' })
    } catch {
      // ignore
    }
  }, [user])

  const clearAll = useCallback(async () => {
    setWords([])
    writeWrongWordsToStorage([])
    if (!user) return
    try {
      await apiFetch('/api/ai/wrong-words', { method: 'DELETE' })
    } catch {
      // ignore
    }
  }, [user])

  return { words, loading, addWord, removeWord, clearAll, refetch: fetchWords }
}
