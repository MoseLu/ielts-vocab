import { z } from 'zod'
import { apiFetch, safeParse } from '../../lib'
import {
  buildSessionPayload,
  clearActiveStudySessionSnapshot,
  consumeStudySessionRecoverySkip,
  markStudySessionRecoveryHandled,
  matchesStudySessionContext,
  normalizeChapterId,
  normalizeEpochMs,
  PASSIVE_STUDY_SESSION_MIN_SECONDS,
  persistStudySessionPayload,
  postStudySessionKeepalive,
  readActiveStudySessionSnapshot,
  recoverPendingStudySession,
  resolveStudySessionDurationSeconds,
  sendStudySessionBeacon,
  shouldDiscardPassiveSession,
  STUDY_SESSION_IDLE_GRACE_MS,
  writeActiveStudySessionSnapshot,
  type FinalizeStudySessionSegmentInput,
  type FinalizeStudySessionSegmentResult,
  type PrepareStudySessionForLearningActionInput,
  type PrepareStudySessionForLearningActionResult,
  type SessionSnapshotPatch,
  type StudySessionContext,
} from './sessionTrackingShared'

const ModePerformanceSchema = z.record(
  z.string(),
  z.object({ correct: z.number(), wrong: z.number() }).passthrough(),
)

export {
  markStudySessionRecoveryHandled,
  PASSIVE_STUDY_SESSION_MIN_SECONDS,
  resolveStudySessionDurationSeconds,
  STUDY_SESSION_IDLE_GRACE_MS,
}

export async function startSession(
  ctx?: StudySessionContext,
  options?: {
    skipRecovery?: boolean
    startedAt?: number
    forceNewSession?: boolean
  },
): Promise<number | null> {
  const startedAt = normalizeEpochMs(options?.startedAt)
  try {
    if (!options?.skipRecovery && !consumeStudySessionRecoverySkip(startedAt)) {
      await recoverPendingStudySession()
    }
    const res = await apiFetch<{ sessionId: number }>('/api/ai/start-session', {
      method: 'POST',
      keepalive: true,
      body: JSON.stringify({
        mode: ctx?.mode ?? 'smart',
        bookId: ctx?.bookId ?? undefined,
        chapterId: ctx?.chapterId != null && ctx.chapterId !== '' ? String(ctx.chapterId) : undefined,
        startedAt,
        forceNewSession: options?.forceNewSession || undefined,
      }),
    })

    if (res.sessionId) {
      writeActiveStudySessionSnapshot({
        version: 1,
        sessionId: res.sessionId,
        mode: ctx?.mode ?? 'smart',
        bookId: ctx?.bookId ?? null,
        chapterId: normalizeChapterId(ctx?.chapterId),
        startedAt,
        lastActiveAt: startedAt,
        wordsStudied: 0,
        correctCount: 0,
        wrongCount: 0,
      })
    }

    return res.sessionId ?? null
  } catch {
    return null
  }
}

export async function cancelSession(sessionId?: number | null): Promise<void> {
  if (!sessionId) return
  try {
    await apiFetch('/api/ai/cancel-session', {
      method: 'POST',
      keepalive: true,
      body: JSON.stringify({ sessionId }),
    })
    clearActiveStudySessionSnapshot(sessionId)
  } catch {
    // Non-critical.
  }
}

export function updateStudySessionSnapshot(patch: SessionSnapshotPatch): void {
  const snapshot = readActiveStudySessionSnapshot()
  if (!snapshot) return
  if (patch.sessionId != null && patch.sessionId !== snapshot.sessionId) return

  writeActiveStudySessionSnapshot({
    ...snapshot,
    mode: patch.mode ?? snapshot.mode,
    bookId: patch.bookId !== undefined ? (patch.bookId ?? null) : snapshot.bookId,
    chapterId: patch.chapterId !== undefined ? normalizeChapterId(patch.chapterId) : snapshot.chapterId,
    startedAt: patch.startedAt ?? snapshot.startedAt,
    lastActiveAt: patch.activeAt == null
      ? snapshot.lastActiveAt
      : Math.max(snapshot.lastActiveAt, patch.activeAt),
    wordsStudied: patch.wordsStudied ?? snapshot.wordsStudied,
    correctCount: patch.correctCount ?? snapshot.correctCount,
    wrongCount: patch.wrongCount ?? snapshot.wrongCount,
  })
}

export function touchStudySessionActivity(sessionId?: number | null, activeAt = Date.now()): void {
  updateStudySessionSnapshot({ sessionId, activeAt })
}

export function isStudySessionActive(data: {
  sessionId?: number | null
  startedAt?: number
  lastActiveAt?: number
}, now = Date.now()): boolean {
  const startedAt = normalizeEpochMs(data.startedAt, 0)
  if (startedAt <= 0) return false

  const snapshot = data.sessionId != null ? readActiveStudySessionSnapshot() : null
  const snapshotLastActiveAt = (
    snapshot
    && data.sessionId != null
    && snapshot.sessionId === data.sessionId
  )
    ? snapshot.lastActiveAt
    : null
  const anchor = snapshotLastActiveAt ?? normalizeEpochMs(data.lastActiveAt, startedAt)
  return now <= anchor + STUDY_SESSION_IDLE_GRACE_MS
}

export async function finalizeStudySessionSegment(
  data: FinalizeStudySessionSegmentInput,
): Promise<FinalizeStudySessionSegmentResult> {
  const sessionId = data.sessionId ?? null
  if (data.startedAt <= 0) {
    return { discarded: true, durationSeconds: 0 }
  }

  if (sessionId) {
    updateStudySessionSnapshot({
      sessionId,
      mode: data.mode,
      bookId: data.bookId,
      chapterId: data.chapterId,
      startedAt: data.startedAt,
      wordsStudied: data.wordsStudied,
      correctCount: data.correctCount,
      wrongCount: data.wrongCount,
    })
  }

  const payload = buildSessionPayload({
    sessionId,
    mode: data.mode,
    bookId: data.bookId,
    chapterId: data.chapterId,
    wordsStudied: data.wordsStudied,
    correctCount: data.correctCount,
    wrongCount: data.wrongCount,
    durationSeconds: resolveStudySessionDurationSeconds({
      sessionId,
      startedAt: data.startedAt,
      endedAt: data.endedAt,
    }),
    startedAt: data.startedAt,
    endedAt: data.endedAt,
  })

  markStudySessionRecoveryHandled()
  if (shouldDiscardPassiveSession(payload)) {
    await cancelSession(sessionId)
    return { discarded: true, durationSeconds: 0 }
  }

  await persistStudySessionPayload(payload, sessionId)
  return { discarded: false, durationSeconds: payload.durationSeconds }
}

export async function prepareStudySessionForLearningAction(
  data: PrepareStudySessionForLearningActionInput,
): Promise<PrepareStudySessionForLearningActionResult> {
  const activityAt = normalizeEpochMs(data.activityAt)
  const startedAt = normalizeEpochMs(data.startedAt, 0)
  const snapshot = data.sessionId != null ? readActiveStudySessionSnapshot() : null
  const matchingSnapshot = (
    snapshot
    && data.sessionId != null
    && snapshot.sessionId === data.sessionId
  )
    ? snapshot
    : null
  const previousLastActiveAt = matchingSnapshot?.lastActiveAt
    ?? normalizeEpochMs(data.lastActiveAt, startedAt > 0 ? startedAt : activityAt)
  const hasOpenSegment = startedAt > 0
  const shouldContinueExistingSegment = (
    hasOpenSegment
    && previousLastActiveAt + STUDY_SESSION_IDLE_GRACE_MS >= activityAt
    && (!matchingSnapshot || matchesStudySessionContext(matchingSnapshot, data))
  )

  if (shouldContinueExistingSegment) {
    if (data.sessionId != null) {
      updateStudySessionSnapshot({
        sessionId: data.sessionId,
        mode: data.mode,
        bookId: data.bookId,
        chapterId: data.chapterId,
        startedAt,
        activeAt: activityAt,
        wordsStudied: data.wordsStudied,
        correctCount: data.correctCount,
        wrongCount: data.wrongCount,
      })
    }
    return {
      sessionId: data.sessionId ?? null,
      startedAt,
      lastActiveAt: activityAt,
      continuedSegment: true,
      segmented: false,
      finalizedPreviousSegment: null,
    }
  }

  let finalizedPreviousSegment: FinalizeStudySessionSegmentResult | null = null
  if (hasOpenSegment) {
    finalizedPreviousSegment = await finalizeStudySessionSegment({
      sessionId: data.sessionId,
      mode: data.mode,
      bookId: data.bookId,
      chapterId: data.chapterId,
      wordsStudied: data.wordsStudied,
      correctCount: data.correctCount,
      wrongCount: data.wrongCount,
      startedAt,
      endedAt: Math.max(startedAt, Math.min(activityAt, previousLastActiveAt + STUDY_SESSION_IDLE_GRACE_MS)),
    })
  }

  const newSessionId = await startSession(
    {
      mode: data.mode,
      bookId: data.bookId,
      chapterId: data.chapterId,
    },
    {
      startedAt: activityAt,
      forceNewSession: hasOpenSegment,
    },
  )

  return {
    sessionId: newSessionId,
    startedAt: activityAt,
    lastActiveAt: activityAt,
    continuedSegment: false,
    segmented: hasOpenSegment,
    finalizedPreviousSegment,
  }
}

export function flushStudySessionOnPageHide(data: {
  mode: string
  bookId?: string | null
  chapterId?: string | null
  wordsStudied: number
  correctCount: number
  wrongCount: number
  startedAt: number
  sessionId?: number | null
}): void {
  const sessionId = data.sessionId ?? null
  const endedAt = Date.now()
  const durationSeconds = resolveStudySessionDurationSeconds({
    sessionId,
    startedAt: data.startedAt,
    endedAt,
  })

  if (sessionId) {
    updateStudySessionSnapshot({
      sessionId,
      mode: data.mode,
      bookId: data.bookId,
      chapterId: data.chapterId,
      startedAt: data.startedAt,
      wordsStudied: data.wordsStudied,
      correctCount: data.correctCount,
      wrongCount: data.wrongCount,
    })
  }

  const payload = buildSessionPayload({
    sessionId,
    mode: data.mode,
    bookId: data.bookId,
    chapterId: data.chapterId,
    wordsStudied: data.wordsStudied,
    correctCount: data.correctCount,
    wrongCount: data.wrongCount,
    durationSeconds,
    startedAt: data.startedAt,
    endedAt,
  })

  if (!sessionId) return

  if (shouldDiscardPassiveSession(payload)) {
    if (!sendStudySessionBeacon('/api/ai/cancel-session', { sessionId })) {
      postStudySessionKeepalive('/api/ai/cancel-session', { sessionId })
    }
    return
  }

  if (!sendStudySessionBeacon('/api/ai/log-session', payload)) {
    postStudySessionKeepalive('/api/ai/log-session', payload)
  }
}

export async function logSession(data: {
  mode: string
  bookId?: string | null
  chapterId?: string | null
  wordsStudied: number
  correctCount: number
  wrongCount: number
  durationSeconds: number
  startedAt: number
  sessionId?: number | null
  endedAt?: number
}) {
  const payload = buildSessionPayload({
    sessionId: data.sessionId,
    mode: data.mode,
    bookId: data.bookId,
    chapterId: data.chapterId,
    wordsStudied: data.wordsStudied,
    correctCount: data.correctCount,
    wrongCount: data.wrongCount,
    durationSeconds: data.durationSeconds,
    startedAt: data.startedAt,
    endedAt: data.endedAt,
  })

  if (data.sessionId) {
    updateStudySessionSnapshot({
      sessionId: data.sessionId,
      mode: data.mode,
      bookId: data.bookId,
      chapterId: data.chapterId,
      startedAt: data.startedAt,
      wordsStudied: data.wordsStudied,
      correctCount: data.correctCount,
      wrongCount: data.wrongCount,
    })
  }

  try {
    await persistStudySessionPayload(payload, data.sessionId)
  } catch {
    // Non-critical.
  }
}

export function recordModeAnswer(mode: string, correct: boolean) {
  try {
    const parsed = safeParse(
      ModePerformanceSchema,
      JSON.parse(localStorage.getItem('mode_performance') || '{}'),
    )
    const stored = parsed.success ? parsed.data : {}
    if (!stored[mode]) stored[mode] = { correct: 0, wrong: 0 }
    if (correct) stored[mode].correct += 1
    else stored[mode].wrong += 1
    localStorage.setItem('mode_performance', JSON.stringify(stored))
  } catch {
    // Non-critical.
  }
}
