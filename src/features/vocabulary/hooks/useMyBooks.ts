import { useState, useEffect, useCallback } from 'react'
import { useAuth } from '../../../contexts'

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
      const token = localStorage.getItem('auth_token')
      const res = await fetch('/api/books/my', {
        headers: { Authorization: `Bearer ${token ?? ''}` },
      })
      if (res.ok) {
        const data = await res.json()
        setMyBookIds(new Set(data.book_ids || []))
      }
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
    const token = localStorage.getItem('auth_token')
    const res = await fetch('/api/books/my', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token ?? ''}`,
      },
      body: JSON.stringify({ book_id: bookId }),
    })
    if (res.ok) {
      setMyBookIds(prev => new Set([...prev, bookId]))
    }
  }, [])

  const removeBook = useCallback(async (bookId: string) => {
    const token = localStorage.getItem('auth_token')
    const res = await fetch(`/api/books/my/${bookId}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token ?? ''}` },
    })
    if (res.ok) {
      setMyBookIds(prev => {
        const next = new Set(prev)
        next.delete(bookId)
        return next
      })
    }
  }, [])

  return { myBookIds, myBooks, loading, resolveMyBooks, addBook, removeBook }
}
