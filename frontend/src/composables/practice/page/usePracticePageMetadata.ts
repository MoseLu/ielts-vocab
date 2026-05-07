import { useEffect, type Dispatch, type SetStateAction } from 'react'
import type { Chapter, PracticeMode } from '../../../features/practice/types'
import { apiFetch } from '../../../lib'
import { LearnerProfileSchema, type LearnerProfile as BackendLearnerProfile } from '../../../lib/schemas'
import { safeParse } from '../../../lib/validation'

export function usePracticeBookChapters({
  resolvedPracticeBookId,
  resolvedPracticeChapterId,
  setBookChapters,
  setCurrentChapterTitle,
}: {
  resolvedPracticeBookId: string | null
  resolvedPracticeChapterId: string | null
  setBookChapters: Dispatch<SetStateAction<Chapter[]>>
  setCurrentChapterTitle: Dispatch<SetStateAction<string>>
}) {
  useEffect(() => {
    if (!resolvedPracticeBookId) {
      setBookChapters([])
      return
    }

    let cancelled = false

    apiFetch<{ chapters?: Chapter[] }>(`/api/books/${resolvedPracticeBookId}/chapters`)
      .then((d: { chapters?: Chapter[] }) => {
        if (cancelled) return
        const chapters = d.chapters || []
        setBookChapters(chapters)
        const current = chapters.find(ch => String(ch.id) === String(resolvedPracticeChapterId)) || chapters[0]
        if (current) setCurrentChapterTitle(current.title)
      })
      .catch(() => {
        if (!cancelled) {
          setBookChapters([])
        }
      })

    return () => {
      cancelled = true
    }
  }, [
    resolvedPracticeBookId,
    resolvedPracticeChapterId,
    setBookChapters,
    setCurrentChapterTitle,
  ])
}

export function usePracticeReviewQueueReset({
  bookId,
  chapterId,
  mode,
  reviewMode,
  settings,
  setReviewOffset,
  setQuickMemoryReviewQueueResolved,
}: {
  bookId: string | null
  chapterId: string | null
  mode?: PracticeMode
  reviewMode: boolean
  settings: {
    reviewInterval?: string
    reviewLimit?: string
  }
  setReviewOffset: Dispatch<SetStateAction<number>>
  setQuickMemoryReviewQueueResolved: Dispatch<SetStateAction<boolean>>
}) {
  useEffect(() => {
    if (!bookId) return
    setReviewOffset(0)
    setQuickMemoryReviewQueueResolved(false)
  }, [
    bookId,
    chapterId,
    mode,
    reviewMode,
    settings.reviewInterval,
    settings.reviewLimit,
    setQuickMemoryReviewQueueResolved,
    setReviewOffset,
  ])
}

export function usePracticeLearnerProfile({
  currentDay,
  reviewMode,
  setBackendLearnerProfile,
  userId,
}: {
  currentDay?: number
  reviewMode: boolean
  setBackendLearnerProfile: Dispatch<SetStateAction<BackendLearnerProfile | null>>
  userId: string | number | null
}) {
  useEffect(() => {
    if (reviewMode) {
      setBackendLearnerProfile(null)
      return
    }

    let cancelled = false

    void (async () => {
      try {
        const data = await apiFetch<unknown>('/api/ai/learner-profile')
        const parsed = safeParse(LearnerProfileSchema, data)
        if (!cancelled) {
          setBackendLearnerProfile(parsed.success ? parsed.data : null)
        }
      } catch {
        if (!cancelled) {
          setBackendLearnerProfile(null)
        }
      }
    })()

    return () => {
      cancelled = true
    }
  }, [currentDay, reviewMode, setBackendLearnerProfile, userId])
}
