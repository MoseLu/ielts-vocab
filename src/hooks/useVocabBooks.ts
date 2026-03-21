import { useState, useEffect } from 'react'

const API_BASE = '/api/books'

// ============================================================================
// Type Definitions
// ============================================================================

/** Filter options for fetching vocabulary books */
export interface VocabBooksFilters {
  category?: string
  level?: string
}

/** A vocabulary book / word list */
export interface VocabBook {
  id: string | number
  name: string
  category?: string
  level?: string
  description?: string
  word_count?: number
  [key: string]: unknown
}

/** A single vocabulary word */
export interface VocabWord {
  id: string | number
  word: string
  phonetic?: string
  definition?: string
  definition_zh?: string
  definition_en?: string
  example?: string
  example_zh?: string
  example_en?: string
  [key: string]: unknown
}

/** Book progress record */
export interface BookProgress {
  book_id: string | number
  current_index: number
  total_words: number
  completed_words: number
  last_learned_at?: string
  [key: string]: unknown
}

/** Progress map: bookId -> BookProgress */
export type ProgressMap = Record<string | number, BookProgress>

// ============================================================================
// Hooks
// ============================================================================

/** Fetch vocabulary books with optional filters */
export function useVocabBooks(filters: VocabBooksFilters = {}) {
  const [books, setBooks] = useState<VocabBook[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchBooks = async () => {
      try {
        setLoading(true)
        const params = new URLSearchParams()
        if (filters.category) params.append('category', filters.category)
        if (filters.level) params.append('level', filters.level)

        const response = await fetch(`${API_BASE}?${params.toString()}`)
        if (!response.ok) throw new Error('Failed to fetch books')

        const data: { books: VocabBook[] } = await response.json()
        setBooks(data.books)
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err))
      } finally {
        setLoading(false)
      }
    }

    fetchBooks()
  }, [filters.category, filters.level])

  return { books, loading, error }
}

/** Fetch words for a specific book with pagination */
export function useBookWords(
  bookId: string | number | null,
  page = 1,
  perPage = 100
) {
  const [words, setWords] = useState<VocabWord[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!bookId) return

    const fetchWords = async () => {
      try {
        setLoading(true)
        const response = await fetch(
          `${API_BASE}/${bookId}/words?page=${page}&per_page=${perPage}`
        )
        if (!response.ok) throw new Error('Failed to fetch words')

        const data: { words: VocabWord[]; total: number } = await response.json()
        setWords(data.words)
        setTotal(data.total)
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err))
      } finally {
        setLoading(false)
      }
    }

    fetchWords()
  }, [bookId, page, perPage])

  return { words, total, loading, error }
}

/** Fetch and save progress for a specific book */
export function useBookProgress(bookId: string | number | null) {
  const [progress, setProgress] = useState<BookProgress | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!bookId) return

    const fetchProgress = async () => {
      try {
        const token = localStorage.getItem('auth_token')
        if (!token) {
          setLoading(false)
          return
        }

        const response = await fetch(`${API_BASE}/progress/${bookId}`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        })

        if (response.ok) {
          const data: { progress: BookProgress } = await response.json()
          setProgress(data.progress)
        }
      } catch (err) {
        console.error('Failed to fetch progress:', err)
      } finally {
        setLoading(false)
      }
    }

    fetchProgress()
  }, [bookId])

  const saveProgress = async (progressData: Partial<BookProgress>): Promise<BookProgress | null> => {
    try {
      const token = localStorage.getItem('auth_token')
      if (!token || !bookId) return null

      const response = await fetch(`${API_BASE}/progress`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ book_id: bookId, ...progressData }),
      })

      if (response.ok) {
        const data: { progress: BookProgress } = await response.json()
        setProgress(data.progress)
        return data.progress
      }
    } catch (err) {
      console.error('Failed to save progress:', err)
    }
    return null
  }

  return { progress, loading, saveProgress }
}

/** Fetch progress for all books */
export function useAllBookProgress() {
  const [progressMap, setProgressMap] = useState<ProgressMap>({})
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchProgress = async () => {
      try {
        const token = localStorage.getItem('auth_token')
        if (!token) {
          setLoading(false)
          return
        }

        const response = await fetch(`${API_BASE}/progress`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        })

        if (response.ok) {
          const data: { progress: ProgressMap } = await response.json()
          setProgressMap(data.progress)
        }
      } catch (err) {
        console.error('Failed to fetch progress:', err)
      } finally {
        setLoading(false)
      }
    }

    fetchProgress()
  }, [])

  return { progressMap, loading }
}
