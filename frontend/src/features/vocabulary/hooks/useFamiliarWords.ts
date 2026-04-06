import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { Word } from '../../../components/practice/types'
import { apiFetch } from '../../../lib'

type ToastType = 'success' | 'error' | 'info'

interface FamiliarContext {
  bookId?: string | null
  chapterId?: string | null
  chapterTitle?: string | null
}

interface UseFamiliarWordsParams {
  userId: string | number | null
  vocabulary: Word[]
  showToast?: (message: string, type?: ToastType) => void
}

function normalizeFamiliarWord(value: string | null | undefined): string {
  return typeof value === 'string' ? value.trim().toLowerCase() : ''
}

function updateFamiliarMembership(previous: Set<string>, normalized: string, active: boolean): Set<string> {
  const next = new Set(previous)
  if (active) next.add(normalized)
  else next.delete(normalized)
  return next
}

export function useFamiliarWords({
  userId,
  vocabulary,
  showToast,
}: UseFamiliarWordsParams) {
  const [familiarWords, setFamiliarWords] = useState<Set<string>>(new Set())
  const [pendingWords, setPendingWords] = useState<Set<string>>(new Set())
  const mutationVersionRef = useRef(0)

  const vocabularyWords = useMemo(() => {
    const uniqueWords: string[] = []
    const seen = new Set<string>()
    for (const word of vocabulary) {
      const normalized = normalizeFamiliarWord(word.word)
      if (!normalized || seen.has(normalized)) continue
      seen.add(normalized)
      uniqueWords.push(normalized)
    }
    return uniqueWords
  }, [vocabulary])

  useEffect(() => {
    let cancelled = false
    const statusRequestVersion = mutationVersionRef.current

    if (!userId || vocabularyWords.length === 0) {
      setFamiliarWords(new Set())
      return () => {
        cancelled = true
      }
    }

    void apiFetch<{ words?: string[] }>('/api/books/familiar/status', {
      method: 'POST',
      body: JSON.stringify({ words: vocabularyWords }),
    }).then(data => {
      if (cancelled || statusRequestVersion !== mutationVersionRef.current) return
      setFamiliarWords(new Set((data.words ?? []).map(normalizeFamiliarWord).filter(Boolean)))
    }).catch(() => {
      if (cancelled || statusRequestVersion !== mutationVersionRef.current) return
      setFamiliarWords(new Set())
    })

    return () => {
      cancelled = true
    }
  }, [userId, vocabularyWords])

  const isFamiliar = useCallback((word: string | null | undefined) => {
    const normalized = normalizeFamiliarWord(word)
    return normalized ? familiarWords.has(normalized) : false
  }, [familiarWords])

  const isPending = useCallback((word: string | null | undefined) => {
    const normalized = normalizeFamiliarWord(word)
    return normalized ? pendingWords.has(normalized) : false
  }, [pendingWords])

  const toggleFamiliar = useCallback(async (word: Word, context?: FamiliarContext) => {
    const normalized = normalizeFamiliarWord(word.word)
    if (!normalized) return

    if (!userId) {
      showToast?.('登录后才能标记熟字', 'info')
      return
    }

    setPendingWords(previous => new Set(previous).add(normalized))
    const currentlyFamiliar = familiarWords.has(normalized)
    const nextFamiliar = !currentlyFamiliar
    mutationVersionRef.current += 1
    setFamiliarWords(previous => updateFamiliarMembership(previous, normalized, nextFamiliar))

    try {
      if (currentlyFamiliar) {
        await apiFetch('/api/books/familiar', {
          method: 'DELETE',
          body: JSON.stringify({ word: word.word }),
        })
        showToast?.('已取消熟字标记', 'success')
        return
      }

      await apiFetch('/api/books/familiar', {
        method: 'POST',
        body: JSON.stringify({
          word: word.word,
          phonetic: word.phonetic,
          pos: word.pos,
          definition: word.definition,
          book_id: word.book_id ?? context?.bookId ?? null,
          book_title: word.book_title ?? null,
          chapter_id: word.chapter_id ?? context?.chapterId ?? null,
          chapter_title: word.chapter_title ?? context?.chapterTitle ?? null,
        }),
      })
      showToast?.('已标记为熟字', 'success')
    } catch (error) {
      setFamiliarWords(previous => updateFamiliarMembership(previous, normalized, currentlyFamiliar))
      showToast?.(error instanceof Error ? error.message : '熟字标记失败，请稍后重试', 'error')
    } finally {
      setPendingWords(previous => {
        const next = new Set(previous)
        next.delete(normalized)
        return next
      })
    }
  }, [familiarWords, showToast, userId])

  return {
    isFamiliar,
    isPending,
    toggleFamiliar,
  }
}
