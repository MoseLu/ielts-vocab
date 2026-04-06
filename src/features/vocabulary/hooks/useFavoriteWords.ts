import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { Word } from '../../../components/practice/types'
import { apiFetch } from '../../../lib'

type ToastType = 'success' | 'error' | 'info'

interface FavoriteContext {
  bookId?: string | null
  chapterId?: string | null
  chapterTitle?: string | null
}

interface UseFavoriteWordsParams {
  userId: string | number | null
  vocabulary: Word[]
  showToast?: (message: string, type?: ToastType) => void
}

function normalizeFavoriteWord(value: string | null | undefined): string {
  return typeof value === 'string' ? value.trim().toLowerCase() : ''
}

function updateFavoriteMembership(previous: Set<string>, normalized: string, active: boolean): Set<string> {
  const next = new Set(previous)
  if (active) next.add(normalized)
  else next.delete(normalized)
  return next
}

export function useFavoriteWords({
  userId,
  vocabulary,
  showToast,
}: UseFavoriteWordsParams) {
  const [favoriteWords, setFavoriteWords] = useState<Set<string>>(new Set())
  const [pendingWords, setPendingWords] = useState<Set<string>>(new Set())
  const mutationVersionRef = useRef(0)

  const vocabularyWords = useMemo(() => {
    const uniqueWords: string[] = []
    const seen = new Set<string>()
    for (const word of vocabulary) {
      const normalized = normalizeFavoriteWord(word.word)
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
      setFavoriteWords(new Set())
      return () => {
        cancelled = true
      }
    }

    void apiFetch<{ words?: string[] }>('/api/books/favorites/status', {
      method: 'POST',
      body: JSON.stringify({ words: vocabularyWords }),
    }).then(data => {
      if (cancelled || statusRequestVersion !== mutationVersionRef.current) return
      setFavoriteWords(new Set((data.words ?? []).map(normalizeFavoriteWord).filter(Boolean)))
    }).catch(() => {
      if (cancelled || statusRequestVersion !== mutationVersionRef.current) return
      setFavoriteWords(new Set())
    })

    return () => {
      cancelled = true
    }
  }, [userId, vocabularyWords])

  const isFavorite = useCallback((word: string | null | undefined) => {
    const normalized = normalizeFavoriteWord(word)
    return normalized ? favoriteWords.has(normalized) : false
  }, [favoriteWords])

  const isPending = useCallback((word: string | null | undefined) => {
    const normalized = normalizeFavoriteWord(word)
    return normalized ? pendingWords.has(normalized) : false
  }, [pendingWords])

  const toggleFavorite = useCallback(async (word: Word, context?: FavoriteContext) => {
    const normalized = normalizeFavoriteWord(word.word)
    if (!normalized) return

    if (!userId) {
      showToast?.('登录后才能收藏单词', 'info')
      return
    }

    setPendingWords(previous => new Set(previous).add(normalized))
    const currentlyFavorite = favoriteWords.has(normalized)
    const nextFavorite = !currentlyFavorite
    mutationVersionRef.current += 1
    setFavoriteWords(previous => updateFavoriteMembership(previous, normalized, nextFavorite))

    try {
      if (currentlyFavorite) {
        await apiFetch('/api/books/favorites', {
          method: 'DELETE',
          body: JSON.stringify({ word: word.word }),
        })
        showToast?.('已取消收藏', 'success')
        return
      }

      await apiFetch('/api/books/favorites', {
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
      showToast?.('已加入收藏词书', 'success')
    } catch (error) {
      setFavoriteWords(previous => updateFavoriteMembership(previous, normalized, currentlyFavorite))
      showToast?.(error instanceof Error ? error.message : '收藏失败，请稍后重试', 'error')
    } finally {
      setPendingWords(previous => {
        const next = new Set(previous)
        next.delete(normalized)
        return next
      })
    }
  }, [favoriteWords, showToast, userId])

  return {
    isFavorite,
    isPending,
    toggleFavorite,
  }
}
