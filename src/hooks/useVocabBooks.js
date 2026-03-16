import { useState, useEffect } from 'react'

const API_BASE = '/api/books'

export function useVocabBooks(filters = {}) {
  const [books, setBooks] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const fetchBooks = async () => {
      try {
        setLoading(true)
        const params = new URLSearchParams()
        if (filters.category) params.append('category', filters.category)
        if (filters.level) params.append('level', filters.level)

        const response = await fetch(`${API_BASE}?${params.toString()}`)
        if (!response.ok) throw new Error('Failed to fetch books')

        const data = await response.json()
        setBooks(data.books)
      } catch (err) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    fetchBooks()
  }, [filters.category, filters.level])

  return { books, loading, error }
}

export function useBookWords(bookId, page = 1, perPage = 100) {
  const [words, setWords] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!bookId) return

    const fetchWords = async () => {
      try {
        setLoading(true)
        const response = await fetch(`${API_BASE}/${bookId}/words?page=${page}&per_page=${perPage}`)
        if (!response.ok) throw new Error('Failed to fetch words')

        const data = await response.json()
        setWords(data.words)
        setTotal(data.total)
      } catch (err) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    fetchWords()
  }, [bookId, page, perPage])

  return { words, total, loading, error }
}

export function useBookProgress(bookId) {
  const [progress, setProgress] = useState(null)
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
            'Authorization': `Bearer ${token}`
          }
        })

        if (response.ok) {
          const data = await response.json()
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

  const saveProgress = async (progressData) => {
    try {
      const token = localStorage.getItem('auth_token')
      if (!token) return null

      const response = await fetch(`${API_BASE}/progress`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ book_id: bookId, ...progressData })
      })

      if (response.ok) {
        const data = await response.json()
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

export function useAllBookProgress() {
  const [progressMap, setProgressMap] = useState({})
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
            'Authorization': `Bearer ${token}`
          }
        })

        if (response.ok) {
          const data = await response.json()
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