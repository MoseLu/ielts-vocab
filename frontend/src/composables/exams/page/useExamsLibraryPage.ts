import { useEffect, useMemo, useState } from 'react'

import type { ExamPaperSummary } from '../../../lib'
import { listExamPapers } from '../../../features/exams/examApi'


interface ExamCollectionGroup {
  key: string
  title: string
  papers: ExamPaperSummary[]
}

function comparePapers(left: ExamPaperSummary, right: ExamPaperSummary) {
  const leftSeries = left.seriesNumber ?? 0
  const rightSeries = right.seriesNumber ?? 0
  if (leftSeries !== rightSeries) return rightSeries - leftSeries
  const leftTest = left.testNumber ?? 0
  const rightTest = right.testNumber ?? 0
  return leftTest - rightTest
}

export function useExamsLibraryPage() {
  const [items, setItems] = useState<ExamPaperSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true

    async function load() {
      setLoading(true)
      setError('')
      try {
        const response = await listExamPapers()
        if (!active) return
        setItems([...response.items].sort(comparePapers))
      } catch (nextError) {
        if (!active) return
        setError(nextError instanceof Error ? nextError.message : '真题题库加载失败')
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

  const collections = useMemo<ExamCollectionGroup[]>(() => {
    const grouped = new Map<string, ExamPaperSummary[]>()
    items.forEach(item => {
      const key = item.collectionTitle || 'IELTS ACADEMIC'
      const current = grouped.get(key) || []
      current.push(item)
      grouped.set(key, current)
    })
    return Array.from(grouped.entries()).map(([key, papers]) => ({
      key,
      title: key,
      papers: [...papers].sort(comparePapers),
    }))
  }, [items])

  return {
    collections,
    loading,
    error,
  }
}
