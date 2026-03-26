import { useState, useEffect, useCallback } from 'react'
import { useAuth } from '../../../contexts'
import { apiFetch } from '../../../lib'

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
    if (!user) {
      setLoading(false)
      return
    }
    try {
      const data = await apiFetch<{ words?: WrongWord[] }>('/api/ai/wrong-words')
      setWords(data.words || [])
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
      if (prev.find(w => w.word === word.word)) return prev
      return [{ ...word, wrong_count: 1 }, ...prev]
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
    setWords(prev => prev.filter(w => w.word !== word))
    if (!user) return
    try {
      await apiFetch(`/api/ai/wrong-words/${encodeURIComponent(word)}`, { method: 'DELETE' })
    } catch {
      // ignore
    }
  }, [user])

  const clearAll = useCallback(async () => {
    setWords([])
    if (!user) return
    try {
      await apiFetch('/api/ai/wrong-words', { method: 'DELETE' })
    } catch {
      // ignore
    }
  }, [user])

  return { words, loading, addWord, removeWord, clearAll, refetch: fetchWords }
}
