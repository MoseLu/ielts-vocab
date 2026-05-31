import { useRef } from 'react'
import type { PracticeGroupWindow } from '../../../composables/practice/page/practicePageGrouping'
import { useQuickMemorySession } from '../../../composables/practice/quick-memory/useQuickMemorySession'
import type { QuickMemoryRecordState } from '../../../lib/quickMemory'
import type { LearningScope } from '../../../lib/learningScope'
import type {
  QuickMemoryModeVariant,
  QuickMemorySessionResult as SessionResult,
} from '../../../features/practice/quickMemorySession'
import { useQuickMemoryModeSession } from './useQuickMemoryModeSession'

interface QuickMemoryModeRuntimeArgs {
  modeVariant: QuickMemoryModeVariant
  bookId: string | null
  chapterId: string | null
  done: boolean
  index: number
  queueWords: string[]
  queueLength: number
  chapterGroup?: PracticeGroupWindow | null
  chapterQueueWords?: string[]
  reviewMode?: boolean
  results: SessionResult[]
  quickMemoryScope: LearningScope
  showSaveError: () => void
  onCompletedSessionDurationChange: (seconds: number) => void
}

export function useQuickMemoryModeRuntime({
  modeVariant,
  bookId,
  chapterId,
  done,
  index,
  queueWords,
  queueLength,
  chapterGroup,
  chapterQueueWords,
  reviewMode,
  results,
  quickMemoryScope,
  showSaveError,
  onCompletedSessionDurationChange,
}: QuickMemoryModeRuntimeArgs) {
  const resultsRef = useRef<SessionResult[]>([])
  const sessionStartRef = useRef(0)
  const sessionLastActiveAtRef = useRef(0)
  const completedSessionDurationSecondsRef = useRef<number | null>(null)
  const bookIdRef = useRef<string | null>(bookId)
  const chapterIdRef = useRef<string | null>(chapterId)
  const sessionIdRef = useRef<number | null>(null)
  const sessionLoggedRef = useRef(false)
  const pendingRecordSyncRef = useRef<Record<string, QuickMemoryRecordState>>({})
  const recordSyncInFlightRef = useRef(false)
  const recordSyncPromiseRef = useRef<Promise<void> | null>(null)

  const controls = useQuickMemoryModeSession({
    modeVariant,
    bookId,
    chapterId,
    bookIdRef,
    chapterIdRef,
    resultsRef,
    sessionStartRef,
    sessionLastActiveAtRef,
    completedSessionDurationSecondsRef,
    sessionIdRef,
    sessionLoggedRef,
    pendingRecordSyncRef,
    recordSyncInFlightRef,
    recordSyncPromiseRef,
    quickMemoryScope,
  })

  useQuickMemorySession({
    modeVariant,
    bookId,
    chapterId,
    done,
    index,
    queueWords,
    queueLength,
    chapterGroup,
    chapterQueueWords,
    reviewMode,
    results,
    resultsRef,
    sessionStartRef,
    sessionLastActiveAtRef,
    completedSessionDurationSecondsRef,
    bookIdRef,
    chapterIdRef,
    sessionIdRef,
    sessionLoggedRef,
    flushPendingRecordSync: controls.flushPendingRecordSync,
    completeCurrentSession: controls.completeCurrentSession,
    syncSessionSnapshot: controls.syncSessionSnapshot,
    showSaveError,
    onCompletedSessionDurationChange,
  })

  return {
    ...controls,
    completedSessionDurationSecondsRef,
    pendingRecordSyncRef,
    resultsRef,
    sessionLoggedRef,
  }
}
