import { useState, useEffect, useCallback } from 'react'
import { useAuth } from '../../../contexts'
import { apiFetch } from '../../../lib'

export interface MyBook {
  id: string
  title?: string
  word_count: number
  is_paid?: boolean
  description?: string
}

export function useMyBooks() {
  const { user, isLoading: authLoading = false } = useAuth()
  const userId = user?.id ?? null
  const [myBookIds, setMyBookIds] = useState<Set<string>>(new Set())
  const [myBooks, setMyBooks] = useState<MyBook[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchMyBooks = useCallback(async () => {
    if (authLoading) {
      setLoading(true)
      return
    }

    if (!userId) {
      setMyBookIds(new Set())
      setError(null)
      setLoading(false)
      return
    }

    try {
      setLoading(true)
      setError(null)
      const data = await apiFetch<{ book_ids?: string[] }>('/api/books/my', { cache: 'no-store' })
      setMyBookIds(new Set(data.book_ids || []))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch my books')
    } finally {
      setLoading(false)
    }
  }, [authLoading, userId])

  useEffect(() => {
    fetchMyBooks()
  }, [fetchMyBooks])

  const resolveMyBooks = useCallback((allBooks: MyBook[]) => {
    setMyBooks(allBooks.filter(b => myBookIds.has(b.id)))
  }, [myBookIds])

  const addBook = useCallback(async (bookId: string) => {
    try {
      await apiFetch('/api/books/my', {
        method: 'POST',
        body: JSON.stringify({ book_id: bookId }),
      })
      setMyBookIds(prev => new Set([...prev, bookId]))
    } catch {
      // ignore
    }
  }, [])

  const removeBook = useCallback(async (bookId: string) => {
    try {
      await apiFetch(`/api/books/my/${bookId}`, { method: 'DELETE' })
      setMyBookIds(prev => {
        const next = new Set(prev)
        next.delete(bookId)
        return next
      })
    } catch {
      // ignore
    }
  }, [])

  return { myBookIds, myBooks, loading, error, refetch: fetchMyBooks, resolveMyBooks, addBook, removeBook }
}
