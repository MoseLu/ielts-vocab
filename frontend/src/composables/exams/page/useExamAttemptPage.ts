import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

import type {
  ExamAttempt,
  ExamAttemptResultResponse,
  ExamPaperDetail,
  ExamSection,
} from '../../../lib'
import {
  createExamAttempt,
  type ExamResponseDraft,
  getExamPaper,
  saveExamResponses,
  submitExamAttempt,
} from '../../../features/exams/examApi'


type ResponseMap = Record<number, ExamResponseDraft>

function buildResponseMap(attempt: ExamAttempt | null | undefined): ResponseMap {
  const next: ResponseMap = {}
  ;(attempt?.responses || []).forEach(response => {
    next[response.questionId] = {
      questionId: response.questionId,
      responseText: response.responseText ?? '',
      selectedChoices: [...response.selectedChoices],
      attachmentUrl: response.attachmentUrl ?? null,
      durationSeconds: response.durationSeconds ?? null,
      isCorrect: response.isCorrect ?? null,
      score: response.score ?? null,
      feedback: response.feedback || {},
    }
  })
  return next
}

function toPayload(responseMap: ResponseMap): ExamResponseDraft[] {
  return Object.values(responseMap)
    .filter(item => {
      const hasText = Boolean(item.responseText?.trim())
      const hasChoices = Boolean(item.selectedChoices?.length)
      const hasAttachment = Boolean(item.attachmentUrl)
      const hasFeedback = Boolean(item.feedback && Object.keys(item.feedback).length)
      return hasText || hasChoices || hasAttachment || hasFeedback
    })
    .map(item => ({
      questionId: item.questionId,
      responseText: item.responseText ?? null,
      selectedChoices: item.selectedChoices || [],
      attachmentUrl: item.attachmentUrl ?? null,
      durationSeconds: item.durationSeconds ?? null,
      isCorrect: item.isCorrect ?? null,
      score: item.score ?? null,
      feedback: item.feedback || {},
    }))
}

function resolveInitialSectionId(paper: ExamPaperDetail, requestedSectionType: string | null): number | null {
  const requested = requestedSectionType
    ? paper.sections.find(section => section.sectionType === requestedSectionType)
    : null
  return requested?.id ?? paper.sections[0]?.id ?? null
}

export function useExamAttemptPage(paperId: number, requestedSectionType: string | null) {
  const [paper, setPaper] = useState<ExamPaperDetail | null>(null)
  const [attempt, setAttempt] = useState<ExamAttempt | null>(null)
  const [result, setResult] = useState<ExamAttemptResultResponse | null>(null)
  const [responseMap, setResponseMap] = useState<ResponseMap>({})
  const [activeSectionId, setActiveSectionId] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [pendingSave, setPendingSave] = useState(false)

  const responseMapRef = useRef<ResponseMap>({})

  useEffect(() => {
    responseMapRef.current = responseMap
  }, [responseMap])

  useEffect(() => {
    let active = true

    async function load() {
      setLoading(true)
      setError('')
      setResult(null)
      try {
        const detail = await getExamPaper(paperId)
        if (!active) return
        setPaper(detail.paper)
        const nextSectionId = resolveInitialSectionId(detail.paper, requestedSectionType)
        setActiveSectionId(nextSectionId)
        if (detail.latestAttempt?.status === 'in_progress') {
          setAttempt(detail.latestAttempt)
          setResponseMap(buildResponseMap(detail.latestAttempt))
          return
        }
        const created = await createExamAttempt(paperId)
        if (!active) return
        setAttempt(created.attempt)
        setResponseMap(buildResponseMap(created.attempt))
      } catch (nextError) {
        if (!active) return
        setError(nextError instanceof Error ? nextError.message : '试卷加载失败')
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
  }, [paperId, requestedSectionType])

  const activeSection = useMemo<ExamSection | null>(() => {
    if (!paper || activeSectionId == null) return null
    return paper.sections.find(section => section.id === activeSectionId) || null
  }, [activeSectionId, paper])

  const updateResponse = useCallback((questionId: number, patch: Partial<ExamResponseDraft>) => {
    setResponseMap(current => {
      const existing = current[questionId] || { questionId, responseText: '', selectedChoices: [], feedback: {} }
      return {
        ...current,
        [questionId]: {
          ...existing,
          ...patch,
          questionId,
        },
      }
    })
    setPendingSave(true)
  }, [])

  const flushResponses = useCallback(async (force = false) => {
    if (!attempt || (saving && !force)) return
    if (!pendingSave && !force) return
    const payload = toPayload(responseMapRef.current)
    setSaving(true)
    try {
      const saved = await saveExamResponses(attempt.id, payload)
      setAttempt(saved.attempt)
      setResponseMap(current => ({
        ...buildResponseMap(saved.attempt),
        ...current,
      }))
      setPendingSave(false)
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : '答案保存失败')
    } finally {
      setSaving(false)
    }
  }, [attempt, pendingSave, saving])

  useEffect(() => {
    if (!pendingSave || !attempt || attempt.status === 'submitted') {
      return
    }
    const timerId = window.setTimeout(() => {
      void flushResponses()
    }, 800)
    return () => {
      window.clearTimeout(timerId)
    }
  }, [attempt, flushResponses, pendingSave])

  const submit = useCallback(async () => {
    if (!attempt) return
    setSubmitting(true)
    setError('')
    try {
      await flushResponses(true)
      const submitted = await submitExamAttempt(attempt.id)
      setAttempt(submitted.attempt)
      setResult(submitted)
      setResponseMap(buildResponseMap(submitted.attempt))
      setPendingSave(false)
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : '提交失败')
    } finally {
      setSubmitting(false)
    }
  }, [attempt, flushResponses])

  const elapsedSeconds = useMemo(() => {
    if (!attempt?.startedAt) return 0
    const startedAt = new Date(attempt.startedAt)
    if (Number.isNaN(startedAt.getTime())) return 0
    const endedAt = attempt.submittedAt ? new Date(attempt.submittedAt) : new Date()
    return Math.max(0, Math.round((endedAt.getTime() - startedAt.getTime()) / 1000))
  }, [attempt?.startedAt, attempt?.submittedAt])

  return {
    paper,
    attempt,
    result,
    responseMap,
    activeSection,
    activeSectionId,
    elapsedSeconds,
    loading,
    saving,
    submitting,
    error,
    setActiveSectionId,
    updateResponse,
    flushResponses,
    submit,
  }
}
