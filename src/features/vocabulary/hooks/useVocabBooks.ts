// ── Vocabulary Hooks ────────────────────────────────────────────────────────────

import { useState, useEffect, useCallback } from 'react'
import { z } from 'zod'
import type { Book, BookProgress } from '../../../types'
import {
  safeParse,
  BooksListResponseSchema,
  WordsListResponseSchema,
  BookSchema,
  WordSchema,
  BookProgressSchema,
  ProgressMapSchema,
} from '../../../lib'

const API_BASE = '/api/books'

export interface UseVocabBooksFilters {
  category?: string
  level?: string
  studyType?: string
}

// Inferred types from Zod schemas (align with domain types)
export type VocabBook = z.infer<typeof BookSchema>
export type VocabWord = z.infer<typeof WordSchema>
export type VocabBookProgress = z.infer<typeof BookProgressSchema>

export function useVocabBooks(filters: UseVocabBooksFilters = {}) {
  const [books, setBooks] = useState<Book[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchBooks = async () => {
      try {
        setLoading(true)
        const params = new URLSearchParams()
        if (filters.category) params.append('category', filters.category)
        if (filters.level) params.append('level', filters.level)
        if (filters.studyType) params.append('study_type', filters.studyType)

        const response = await fetch(`${API_BASE}?${params.toString()}`)
        if (!response.ok) throw new Error('Failed to fetch books')

        const raw = await response.json()

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
    }

    fetchBooks()
  }, [filters.category, filters.level])

  return { books, loading, error }
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
        const response = await fetch(`${API_BASE}/${bookId}/words?page=${page}&per_page=${perPage}`)
        if (!response.ok) throw new Error('Failed to fetch words')

        const raw = await response.json()

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
  const [progress, setProgress] = useState<VocabBookProgress | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!bookId) return

    const fetchProgress = async () => {
      try {
        const raw = await fetch(`${API_BASE}/progress/${bookId}`)
          .then(r => r.ok ? r.json() : Promise.reject(new Error('Failed to fetch progress')))

        // Try as single progress object first
        const singleResult = safeParse(BookProgressSchema, raw)
        if (singleResult.success) {
          setProgress(singleResult.data)
          return
        }

        // Try as wrapped { progress } response
        const wrappedResult = safeParse(z.object({ progress: BookProgressSchema }), raw)
        if (wrappedResult.success) {
          setProgress(wrappedResult.data.progress)
        }
      } catch {
        // Progress not found is ok
      } finally {
        setLoading(false)
      }
    }

    fetchProgress()
  }, [bookId])

  const saveProgress = useCallback(async (progressData: Partial<VocabBookProgress>) => {
    try {
      const raw = await fetch(`${API_BASE}/progress`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('auth_token') ?? ''}`,
        },
        body: JSON.stringify({ book_id: bookId, ...progressData }),
      }).then(r => r.json())

      const result = safeParse(z.object({ progress: BookProgressSchema }), raw)
      if (!result.success) {
        console.error('Progress save validation failed:', result.errors)
        return null
      }

      setProgress(result.data.progress)
      return result.data.progress
    } catch (err) {
      console.error('Failed to save progress:', err)
      return null
    }
  }, [bookId])

  return { progress, loading, saveProgress }
}

export function useAllBookProgress() {
  const [progressMap, setProgressMap] = useState<Record<string, VocabBookProgress>>({})
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchProgress = async () => {
      try {
        const raw = await fetch(`${API_BASE}/progress`, {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('auth_token') ?? ''}`,
          },
        }).then(r => r.ok ? r.json() : Promise.reject(new Error('Failed to fetch progress')))

        const result = safeParse(ProgressMapSchema, raw)
        if (result.success) {
          setProgressMap(result.data)
        }
      } catch {
        // No progress found
      } finally {
        setLoading(false)
      }
    }

    fetchProgress()
  }, [])

  return { progressMap, loading }
}
