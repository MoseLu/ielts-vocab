// ── Vocabulary Hooks ────────────────────────────────────────────────────────────

import { useState, useEffect, useCallback } from 'react'
import { z } from 'zod'
import type { Book } from '../../../types'
import {
  apiFetch,
  safeParse,
  BooksListResponseSchema,
  WordsListResponseSchema,
  BookSchema,
  WordSchema,
  BookProgressSchema,
  ProgressMapSchema,
} from '../../../lib'
import { reportFrontendError } from '../../../lib/errorReporting'
import { useAuth } from '../../../contexts'

const API_BASE = '/api/books'

// Inferred types from Zod schemas (align with domain types)
export type VocabBook = z.infer<typeof BookSchema>
export type VocabWord = z.infer<typeof WordSchema>
export type VocabBookProgress = z.infer<typeof BookProgressSchema>

export function useVocabBooks() {
  const [books, setBooks] = useState<Book[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchBooks = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const raw = await apiFetch<unknown>(API_BASE, { cache: 'no-store' })

      // Validate API response with Zod
      const result = safeParse(BooksListResponseSchema, raw)
      if (!result.success) {
        throw new Error('词书数据格式错误')
      }

      setBooks(result.data.books as Book[])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch books')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void fetchBooks()
  }, [fetchBooks])

  return { books, loading, error, refetch: fetchBooks }
}

export function useBookWords(bookId: string, page = 1, perPage = 100) {
  const [words, setWords] = useState<VocabWord[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!bookId) return

    const fetchWords = async () => {
      try {
        setLoading(true)
        const raw = await apiFetch<unknown>(`${API_BASE}/${bookId}/words?page=${page}&per_page=${perPage}`)

        // Validate API response with Zod
        const result = safeParse(WordsListResponseSchema, raw)
        if (!result.success) {
          throw new Error('单词数据格式错误')
        }

        setWords(result.data.words as VocabWord[])
        setTotal(result.data.total)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch words')
      } finally {
        setLoading(false)
      }
    }

    fetchWords()
  }, [bookId, page, perPage])

  return { words, total, loading, error }
}

export function useBookProgress(bookId: string) {
  const { user } = useAuth()
  const [progress, setProgress] = useState<VocabBookProgress | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!bookId || !user) {
      setLoading(false)
      return
    }

    const fetchProgress = async () => {
      try {
        const raw = await apiFetch<unknown>(`${API_BASE}/progress/${bookId}`)
        const wrapped = safeParse(
          z.object({ progress: BookProgressSchema.nullable() }),
          raw,
        )
        if (wrapped.success && wrapped.data.progress) {
          setProgress(wrapped.data.progress)
        }
      } catch {
        // Progress not found is ok
      } finally {
        setLoading(false)
      }
    }

    fetchProgress()
  }, [bookId, user])

  const saveProgress = useCallback(async (progressData: Partial<VocabBookProgress>) => {
    if (!user) return null
    try {
      const raw = await apiFetch<unknown>(`${API_BASE}/progress`, {
        method: 'POST',
        body: JSON.stringify({ book_id: bookId, ...progressData }),
      })

      const result = safeParse(z.object({ progress: BookProgressSchema }), raw)
      if (!result.success) {
        reportFrontendError({
          source: 'http',
          severity: 'warning',
          method: 'POST',
          requestUrl: `${API_BASE}/progress`,
          message: 'Progress save validation failed',
          context: { errors: result.errors },
        })
        return null
      }

      setProgress(result.data.progress)
      return result.data.progress
    } catch {
      return null
    }
  }, [bookId, user])

  return { progress, loading, saveProgress }
}

export function useAllBookProgress() {
  const { user, isLoading: authLoading = false } = useAuth()
  const userId = user?.id ?? null
  const [progressMap, setProgressMap] = useState<Record<string, VocabBookProgress>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchProgress = useCallback(async () => {
    if (authLoading) {
      setLoading(true)
      return
    }

    if (!userId) {
      setProgressMap({})
      setError(null)
      setLoading(false)
      return
    }

    try {
      setLoading(true)
      setError(null)
      const raw = await apiFetch<unknown>(`${API_BASE}/progress`, { cache: 'no-store' })

      const result = safeParse(z.object({ progress: ProgressMapSchema }), raw)
      if (result.success) {
        setProgressMap(result.data.progress)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch progress')
    } finally {
      setLoading(false)
    }
  }, [authLoading, userId])

  useEffect(() => {
    void fetchProgress()
  }, [fetchProgress])

  return { progressMap, loading, error, refetch: fetchProgress }
}
