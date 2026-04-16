import { useEffect, useState } from 'react'
import { apiFetch } from '../../../lib'
import { HomeTodoResponseSchema, type HomeTodoResponse } from '../../../lib/schemas/home-todo'
import { safeParse } from '../../../lib/validation'

const EMPTY_HOME_TODOS: HomeTodoResponse = {
  date: '',
  summary: {
    pending_count: 0,
    completed_count: 0,
    carry_over_count: 0,
    last_generated_at: null,
  },
  primary_items: [],
  overflow_items: [],
}

export function useHomeTodos() {
  const [data, setData] = useState<HomeTodoResponse>(EMPTY_HOME_TODOS)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true

    const load = async () => {
      setLoading(true)

      try {
        const raw = await apiFetch('/api/ai/home-todos')
        if (!active) return
        const parsed = safeParse(HomeTodoResponseSchema, raw)
        if (!parsed.success) {
          setData(EMPTY_HOME_TODOS)
          setError(parsed.errors.join('；'))
          return
        }
        setData(parsed.data)
        setError(null)
      } catch (loadError) {
        if (!active) return
        setData(EMPTY_HOME_TODOS)
        setError(loadError instanceof Error ? loadError.message : '待办加载失败')
      } finally {
        if (active) {
          setLoading(false)
        }
      }
    }

    void load()

    return () => {
      active = false
    }
  }, [])

  return {
    data,
    primaryItems: data.primary_items,
    overflowItems: data.overflow_items,
    summary: data.summary,
    loading,
    error,
  }
}
