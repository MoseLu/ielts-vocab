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

const ModePerformanceSchema = z.record(
  z.string(),
  z.object({ correct: z.number(), wrong: z.number() }).passthrough(),
)

interface ActiveStudySessionSnapshot {
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

type SessionSnapshotPatch = {
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

export const PASSIVE_STUDY_SESSION_MIN_SECONDS = 30
export const STUDY_SESSION_IDLE_GRACE_MS = 5 * 60 * 1000

function normalizeChapterId(value?: string | null): string | null {
  if (value == null) return null
  const text = String(value).trim()
  return text ? text : null
}

function readActiveStudySessionSnapshot(): ActiveStudySessionSnapshot | null {
  const raw = localStorage.getItem('active_study_session')
  if (!raw) return null
  const parsed = safeParse(ActiveStudySessionSchema, JSON.parse(raw))
  return parsed.success ? parsed.data : null
}

function writeActiveStudySessionSnapshot(snapshot: ActiveStudySessionSnapshot): void {
  localStorage.setItem('active_study_session', JSON.stringify(snapshot))
}

function clearActiveStudySessionSnapshot(sessionId?: number | null): void {
  const snapshot = readActiveStudySessionSnapshot()
  if (!snapshot) return
  if (sessionId != null && snapshot.sessionId !== sessionId) return
  localStorage.removeItem('active_study_session')
}

function resolveSnapshotEndAt(snapshot: ActiveStudySessionSnapshot, now = Date.now()): number {
  const graceDeadline = snapshot.lastActiveAt + STUDY_SESSION_IDLE_GRACE_MS
  return Math.max(snapshot.startedAt, Math.min(now, graceDeadline))
}

function normalizeEpochMs(value: unknown, fallback = Date.now()): number {
  const timestamp = Number(value)
  return Number.isFinite(timestamp) ? Math.max(0, Math.trunc(timestamp)) : fallback
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
  const shouldApplyIdleCap = Boolean(
    snapshot
    && snapshot.sessionId === data.sessionId
    && startedAt > 0
  )
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

  return { startedAt, endedAt, durationSeconds, cappedByActivity: shouldApplyIdleCap && endedAt < requestedEndedAt }
}

export function resolveStudySessionDurationSeconds(data: {
  sessionId?: number | null
  startedAt: number
  endedAt?: number
  durationSeconds?: number
}): number {
  return resolveStudySessionTiming(data).durationSeconds
}

function buildSessionPayload(data: {
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
  const payload = {
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
  return payload
}

function shouldDiscardPassiveSession(payload: ReturnType<typeof buildSessionPayload>) {
  return (
    payload.wordsStudied <= 0
    && payload.correctCount <= 0
    && payload.wrongCount <= 0
    && payload.durationSeconds < PASSIVE_STUDY_SESSION_MIN_SECONDS
  )
}

function sendStudySessionBeacon(url: string, payload: unknown): boolean {
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

function postStudySessionKeepalive(url: string, payload: unknown): void {
  fetch(url, {
    method: 'POST',
    credentials: 'include',
    keepalive: true,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  }).catch(() => {})
}

async function recoverPendingStudySession(): Promise<void> {
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
      await apiFetch('/api/ai/log-session', {
        method: 'POST',
        keepalive: true,
        body: JSON.stringify(payload),
      })
    }
    clearActiveStudySessionSnapshot(snapshot.sessionId)
  } catch {
    // Keep the snapshot for the next recovery attempt.
  }
}

export async function startSession(ctx?: {
  mode?: string
  bookId?: string | null
  chapterId?: string | null
}): Promise<number | null> {
  try {
    await recoverPendingStudySession()
    const res = await apiFetch<{ sessionId: number }>('/api/ai/start-session', {
      method: 'POST',
      keepalive: true,
      body: JSON.stringify({
        mode: ctx?.mode ?? 'smart',
        bookId: ctx?.bookId ?? undefined,
        chapterId: ctx?.chapterId != null && ctx.chapterId !== '' ? String(ctx.chapterId) : undefined,
      }),
    })

    if (res.sessionId) {
      const now = Date.now()
      writeActiveStudySessionSnapshot({
        version: 1,
        sessionId: res.sessionId,
        mode: ctx?.mode ?? 'smart',
        bookId: ctx?.bookId ?? null,
        chapterId: normalizeChapterId(ctx?.chapterId),
        startedAt: now,
        lastActiveAt: now,
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

  apiFetch('/api/ai/log-session', {
    method: 'POST',
    keepalive: true,
    body: JSON.stringify(payload),
  })
    .then(() => {
      if (data.sessionId) clearActiveStudySessionSnapshot(data.sessionId)
    })
    .catch(() => {})
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
