import { useEffect, useMemo, useState } from 'react'

import type { ExamPaperDetail, ExamPaperSummary, ExamQuestion } from '../../../lib'
import { getExamPaper, listExamPapers } from '../../../features/exams/examApi'


interface ExamCollectionGroup {
  key: string
  title: string
  papers: ExamPaperSummary[]
}

export type ExamLibraryQuestionFilter =
  | 'fill_blank'
  | 'single_choice'
  | 'multiple_choice'
  | 'matching'
  | 'judgement'

export interface ExamPaperQuestionIndex {
  paperQuestionFilters: ExamLibraryQuestionFilter[]
  sectionQuestionFilters: Record<number, ExamLibraryQuestionFilter[]>
  sectionQuestionIds?: Record<number, number[]>
}

function stripHtml(html: string) {
  return html.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim()
}

function normalizeToken(value: string | null | undefined) {
  return (value || '').replace(/\s+/g, ' ').trim().toLowerCase()
}

function isJudgementQuestion(question: ExamQuestion) {
  const prompt = normalizeToken(stripHtml(question.promptHtml))
  const choiceTokens = question.choices.flatMap(choice => [
    normalizeToken(choice.key),
    normalizeToken(choice.label),
    normalizeToken(stripHtml(choice.contentHtml)),
  ])
  const acceptedTokens = question.acceptedAnswers.map(answer => normalizeToken(answer))
  const tokenSet = new Set([...choiceTokens, ...acceptedTokens].filter(Boolean))

  if (prompt.includes('true false not given') || prompt.includes('yes no not given')) {
    return true
  }

  const trueFalseNotGiven =
    tokenSet.has('true') && tokenSet.has('false') && tokenSet.has('not given')
  const yesNoNotGiven =
    tokenSet.has('yes') && tokenSet.has('no') && tokenSet.has('not given')

  return trueFalseNotGiven || yesNoNotGiven
}

function categorizeQuestion(question: ExamQuestion): ExamLibraryQuestionFilter[] {
  if (question.questionType === 'fill_blank' || question.questionType === 'short_answer') {
    return ['fill_blank']
  }
  if (question.questionType === 'multiple_choice') {
    return ['multiple_choice']
  }
  if (question.questionType === 'matching') {
    return ['matching']
  }
  if (question.questionType === 'single_choice') {
    return [isJudgementQuestion(question) ? 'judgement' : 'single_choice']
  }
  return []
}

function buildQuestionIndex(paper: ExamPaperDetail): ExamPaperQuestionIndex {
  const paperFilters = new Set<ExamLibraryQuestionFilter>()
  const sectionQuestionFilters: Record<number, ExamLibraryQuestionFilter[]> = {}
  const sectionQuestionIds: Record<number, number[]> = {}

  paper.sections.forEach(section => {
    const sectionFilters = new Set<ExamLibraryQuestionFilter>()
    sectionQuestionIds[section.id] = section.questions.map(question => question.id)
    section.questions.forEach(question => {
      categorizeQuestion(question).forEach(filter => {
        sectionFilters.add(filter)
        paperFilters.add(filter)
      })
    })
    sectionQuestionFilters[section.id] = [...sectionFilters]
  })

  return {
    paperQuestionFilters: [...paperFilters],
    sectionQuestionFilters,
    sectionQuestionIds,
  }
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
  const [questionIndexMap, setQuestionIndexMap] = useState<Record<number, ExamPaperQuestionIndex>>({})
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

        const detailResults = await Promise.allSettled(
          response.items.map(item => getExamPaper(item.id)),
        )
        if (!active) return

        const nextQuestionIndexMap: Record<number, ExamPaperQuestionIndex> = {}
        detailResults.forEach(result => {
          if (result.status !== 'fulfilled') return
          const paper = result.value.paper
          nextQuestionIndexMap[paper.id] = buildQuestionIndex(paper)
        })
        setQuestionIndexMap(nextQuestionIndexMap)
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
    questionIndexMap,
    loading,
    error,
  }
}
