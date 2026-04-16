import { z } from 'zod'
import { apiFetch, safeParse } from '../../lib'

const ActiveStudySessionSchema = z.object({
  version: z.literal(1),
  sessionId: z.number().int().positive(),
  mode: z.string(),
  bookId: z.string().nullable(),
  chapterId: z.string().nullable(),
  startedAt: z.number().int().nonnegative(),
  lastActiveAt: z.number().int().nonnegative(),
  wordsStudied: z.number().int().nonnegative(),
  correctCount: z.number().int().nonnegative(),
  wrongCount: z.number().int().nonnegative(),
}).passthrough()

const STUDY_SESSION_SKIP_RECOVERY_UNTIL_KEY = 'active_study_session_skip_recovery_until'

export interface ActiveStudySessionSnapshot {
  version: 1
  sessionId: number
  mode: string
  bookId: string | null
  chapterId: string | null
  startedAt: number
  lastActiveAt: number
  wordsStudied: number
  correctCount: number
  wrongCount: number
}

export type SessionSnapshotPatch = {
  sessionId?: number | null
  mode?: string
  bookId?: string | null
  chapterId?: string | null
  startedAt?: number
  activeAt?: number
  wordsStudied?: number
  correctCount?: number
  wrongCount?: number
}

export type StudySessionContext = {
  mode: string
  bookId?: string | null
  chapterId?: string | null
}

export type StudySessionStats = {
  wordsStudied: number
  correctCount: number
  wrongCount: number
}

export type PrepareStudySessionForLearningActionInput = StudySessionContext & StudySessionStats & {
  sessionId?: number | null
  startedAt?: number
  lastActiveAt?: number
  activityAt?: number
}

export type FinalizeStudySessionSegmentInput = StudySessionContext & StudySessionStats & {
  sessionId?: number | null
  startedAt: number
  endedAt?: number
}

export type FinalizeStudySessionSegmentResult = {
  discarded: boolean
  durationSeconds: number
}

export type PrepareStudySessionForLearningActionResult = {
  sessionId: number | null
  startedAt: number
  lastActiveAt: number
  continuedSegment: boolean
  segmented: boolean
  finalizedPreviousSegment: FinalizeStudySessionSegmentResult | null
}

export const PASSIVE_STUDY_SESSION_MIN_SECONDS = 30
export const STUDY_SESSION_IDLE_GRACE_MS = 5 * 60 * 1000

export function normalizeChapterId(value?: string | null): string | null {
  if (value == null) return null
  const text = String(value).trim()
  return text ? text : null
}

export function normalizeBookId(value?: string | null): string | null {
  if (value == null) return null
  const text = String(value).trim()
  return text ? text : null
}

export function readActiveStudySessionSnapshot(): ActiveStudySessionSnapshot | null {
  const raw = localStorage.getItem('active_study_session')
  if (!raw) return null
  const parsed = safeParse(ActiveStudySessionSchema, JSON.parse(raw))
  return parsed.success ? parsed.data : null
}

export function writeActiveStudySessionSnapshot(snapshot: ActiveStudySessionSnapshot): void {
  localStorage.setItem('active_study_session', JSON.stringify(snapshot))
}

export function clearActiveStudySessionSnapshot(sessionId?: number | null): void {
  const snapshot = readActiveStudySessionSnapshot()
  if (!snapshot) return
  if (sessionId != null && snapshot.sessionId !== sessionId) return
  localStorage.removeItem('active_study_session')
}

export function markStudySessionRecoveryHandled(ttlMs = 15_000): void {
  localStorage.setItem(
    STUDY_SESSION_SKIP_RECOVERY_UNTIL_KEY,
    String(Date.now() + Math.max(1_000, Math.trunc(ttlMs))),
  )
}

export function consumeStudySessionRecoverySkip(now = Date.now()): boolean {
  const raw = localStorage.getItem(STUDY_SESSION_SKIP_RECOVERY_UNTIL_KEY)
  if (!raw) return false
  localStorage.removeItem(STUDY_SESSION_SKIP_RECOVERY_UNTIL_KEY)
  const expiresAt = Number(raw)
  return Number.isFinite(expiresAt) && expiresAt > now
}

export function normalizeEpochMs(value: unknown, fallback = Date.now()): number {
  const timestamp = Number(value)
  return Number.isFinite(timestamp) ? Math.max(0, Math.trunc(timestamp)) : fallback
}

function resolveSnapshotEndAt(snapshot: ActiveStudySessionSnapshot, now = Date.now()): number {
  const graceDeadline = snapshot.lastActiveAt + STUDY_SESSION_IDLE_GRACE_MS
  return Math.max(snapshot.startedAt, Math.min(now, graceDeadline))
}

export function matchesStudySessionContext(
  snapshot: Pick<ActiveStudySessionSnapshot, 'mode' | 'bookId' | 'chapterId'>,
  context: StudySessionContext,
): boolean {
  return (
    snapshot.mode === context.mode
    && normalizeBookId(snapshot.bookId) === normalizeBookId(context.bookId)
    && normalizeChapterId(snapshot.chapterId) === normalizeChapterId(context.chapterId)
  )
}

function resolveStudySessionTiming(data: {
  sessionId?: number | null
  startedAt: number
  endedAt?: number
  durationSeconds?: number
}) {
  const startedAt = normalizeEpochMs(data.startedAt, 0)
  const requestedEndedAt = normalizeEpochMs(data.endedAt)
  const snapshot = data.sessionId != null ? readActiveStudySessionSnapshot() : null
  const shouldApplyIdleCap = Boolean(snapshot && snapshot.sessionId === data.sessionId && startedAt > 0)
  const endedAt = shouldApplyIdleCap
    ? resolveSnapshotEndAt(snapshot as ActiveStudySessionSnapshot, requestedEndedAt)
    : requestedEndedAt
  const derivedDuration = startedAt > 0 && endedAt >= startedAt
    ? Math.max(0, Math.round((endedAt - startedAt) / 1000))
    : 0
  const rawDuration = Math.max(0, Math.trunc(Number(data.durationSeconds ?? 0) || 0))
  const durationSeconds = shouldApplyIdleCap && derivedDuration > 0
    ? derivedDuration
    : Math.max(rawDuration, derivedDuration)

  return {
    startedAt,
    endedAt,
    durationSeconds,
    cappedByActivity: shouldApplyIdleCap && endedAt < requestedEndedAt,
  }
}

export function resolveStudySessionDurationSeconds(data: {
  sessionId?: number | null
  startedAt: number
  endedAt?: number
  durationSeconds?: number
}): number {
  return resolveStudySessionTiming(data).durationSeconds
}

export function buildSessionPayload(data: {
  sessionId?: number | null
  mode: string
  bookId?: string | null
  chapterId?: string | null
  wordsStudied: number
  correctCount: number
  wrongCount: number
  durationSeconds: number
  startedAt: number
  endedAt?: number
}) {
  const timing = resolveStudySessionTiming({
    sessionId: data.sessionId,
    startedAt: data.startedAt,
    endedAt: data.endedAt,
    durationSeconds: data.durationSeconds,
  })
  return {
    sessionId: data.sessionId ?? undefined,
    mode: data.mode,
    bookId: data.bookId ?? undefined,
    chapterId: normalizeChapterId(data.chapterId),
    wordsStudied: Math.max(0, Math.trunc(data.wordsStudied)),
    correctCount: Math.max(0, Math.trunc(data.correctCount)),
    wrongCount: Math.max(0, Math.trunc(data.wrongCount)),
    durationSeconds: timing.durationSeconds,
    startedAt: timing.startedAt,
    endedAt: timing.endedAt,
    durationCappedByActivity: timing.cappedByActivity || undefined,
  }
}

export function shouldDiscardPassiveSession(payload: ReturnType<typeof buildSessionPayload>) {
  return (
    payload.wordsStudied <= 0
    && payload.correctCount <= 0
    && payload.wrongCount <= 0
    && payload.durationSeconds < PASSIVE_STUDY_SESSION_MIN_SECONDS
  )
}

export function sendStudySessionBeacon(url: string, payload: unknown): boolean {
  if (typeof navigator === 'undefined' || typeof navigator.sendBeacon !== 'function') {
    return false
  }

  try {
    const blob = new Blob([JSON.stringify(payload)], { type: 'application/json' })
    return navigator.sendBeacon(url, blob)
  } catch {
    return false
  }
}

export function postStudySessionKeepalive(url: string, payload: unknown): void {
  fetch(url, {
    method: 'POST',
    credentials: 'include',
    keepalive: true,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  }).catch(() => {})
}

export async function persistStudySessionPayload(
  payload: ReturnType<typeof buildSessionPayload>,
  sessionId?: number | null,
): Promise<void> {
  await apiFetch('/api/ai/log-session', {
    method: 'POST',
    keepalive: true,
    body: JSON.stringify(payload),
  })
  clearActiveStudySessionSnapshot(sessionId)
}

export async function recoverPendingStudySession(): Promise<void> {
  const snapshot = readActiveStudySessionSnapshot()
  if (!snapshot) return

  const endedAt = resolveSnapshotEndAt(snapshot)
  const durationSeconds = Math.max(0, Math.round((endedAt - snapshot.startedAt) / 1000))
  const payload = buildSessionPayload({
    sessionId: snapshot.sessionId,
    mode: snapshot.mode,
    bookId: snapshot.bookId,
    chapterId: snapshot.chapterId,
    wordsStudied: snapshot.wordsStudied,
    correctCount: snapshot.correctCount,
    wrongCount: snapshot.wrongCount,
    durationSeconds,
    startedAt: snapshot.startedAt,
    endedAt,
  })

  try {
    if (shouldDiscardPassiveSession(payload)) {
      await apiFetch('/api/ai/cancel-session', {
        method: 'POST',
        keepalive: true,
        body: JSON.stringify({ sessionId: snapshot.sessionId }),
      })
    } else {
      await persistStudySessionPayload(payload, snapshot.sessionId)
    }
    clearActiveStudySessionSnapshot(snapshot.sessionId)
  } catch {
    // Keep the snapshot for the next recovery attempt.
  }
}
