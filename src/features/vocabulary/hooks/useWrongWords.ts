import { useState, useEffect, useCallback } from 'react'

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
  const [words, setWords] = useState<WrongWord[]>([])
  const [loading, setLoading] = useState(true)

  const fetchWords = useCallback(async () => {
    try {
      const token = localStorage.getItem('auth_token')
      const res = await fetch('/api/ai/wrong-words', {
        headers: { Authorization: `Bearer ${token ?? ''}` },
      })
      if (res.ok) {
        const data = await res.json()
        setWords(data.words || [])
      }
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchWords()
  }, [fetchWords])

  const addWord = useCallback(async (word: WrongWord) => {
    // Optimistic update
    setWords(prev => {
      if (prev.find(w => w.word === word.word)) return prev
      return [{ ...word, wrong_count: 1 }, ...prev]
    })
    // Sync to backend
    const token = localStorage.getItem('auth_token')
    await fetch('/api/ai/wrong-words/sync', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token ?? ''}`,
      },
      body: JSON.stringify({ words: [word] }),
    })
  }, [])

  const removeWord = useCallback(async (word: string) => {
    setWords(prev => prev.filter(w => w.word !== word))
    const token = localStorage.getItem('auth_token')
    await fetch(`/api/ai/wrong-words/${encodeURIComponent(word)}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token ?? ''}` },
    })
  }, [])

  const clearAll = useCallback(async () => {
    setWords([])
    const token = localStorage.getItem('auth_token')
    await fetch('/api/ai/wrong-words', {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token ?? ''}` },
    })
  }, [])

  return { words, loading, addWord, removeWord, clearAll, refetch: fetchWords }
}
