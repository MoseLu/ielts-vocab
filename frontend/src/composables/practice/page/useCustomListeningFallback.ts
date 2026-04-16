import { useCallback, useEffect, useRef, useState } from 'react'
import type { PracticeMode, ToastType } from '../../../components/practice/types'
import { isCustomPracticeBookId } from '../../../components/practice/page/practicePageHelpers'

interface UseCustomListeningFallbackParams {
  requestedPracticeMode: PracticeMode
  currentDay?: number
  bookId: string | null
  chapterId: string | null
  resolvedPracticeBookId: string | null
  resolvedPracticeChapterId: string | null
  reviewMode: boolean
  errorMode: boolean
  showToast?: (message: string, type?: ToastType) => void
  onModeChange?: (mode: PracticeMode) => void
}

export function useCustomListeningFallback({
  requestedPracticeMode,
  currentDay,
  bookId,
  chapterId,
  resolvedPracticeBookId,
  resolvedPracticeChapterId,
  reviewMode,
  errorMode,
  showToast,
  onModeChange,
}: UseCustomListeningFallbackParams) {
  const [fallbackScope, setFallbackScope] = useState<string | null>(null)
  const noticeScopeRef = useRef<string | null>(null)
  const practiceScopeKey = `${resolvedPracticeBookId ?? bookId ?? 'day'}:${resolvedPracticeChapterId ?? chapterId ?? currentDay ?? 'all'}:${errorMode ? 'errors' : reviewMode ? 'review' : 'study'}`
  const isCustomPracticeScope = isCustomPracticeBookId(resolvedPracticeBookId ?? bookId)
  const practiceMode: PracticeMode = requestedPracticeMode === 'listening' && fallbackScope === practiceScopeKey
    ? 'meaning'
    : requestedPracticeMode

  useEffect(() => {
    if (requestedPracticeMode !== 'listening' || !isCustomPracticeScope) {
      noticeScopeRef.current = null
    }
  }, [isCustomPracticeScope, requestedPracticeMode])

  const handleCustomListeningFallback = useCallback(() => {
    setFallbackScope(previousScope => (previousScope === practiceScopeKey ? previousScope : practiceScopeKey))
    if (noticeScopeRef.current !== practiceScopeKey) {
      noticeScopeRef.current = practiceScopeKey
      showToast?.('自定义词书当前章节没有听音题素材，已自动切换到词义模式。', 'info')
    }
    onModeChange?.('meaning')
  }, [onModeChange, practiceScopeKey, showToast])

  return {
    isCustomPracticeScope,
    practiceMode,
    handleCustomListeningFallback,
  }
}
