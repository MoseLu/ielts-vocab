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
  const { user } = useAuth()
  const [myBookIds, setMyBookIds] = useState<Set<string>>(new Set())
  const [myBooks, setMyBooks] = useState<MyBook[]>([])
  const [loading, setLoading] = useState(true)

  const fetchMyBooks = useCallback(async () => {
    if (!user) { setMyBookIds(new Set()); setLoading(false); return }
    try {
      const data = await apiFetch<{ book_ids?: string[] }>('/api/books/my')
      setMyBookIds(new Set(data.book_ids || []))
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }, [user])

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

  return { myBookIds, myBooks, loading, resolveMyBooks, addBook, removeBook }
}
