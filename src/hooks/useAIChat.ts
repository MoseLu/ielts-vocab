// ── useAIChat ─────────────────────────────────────────────────────────────────
// Smart AI assistant hook with:
//   - Personalized proactive greeting (calls /api/ai/greet on open)
//   - Cross-session memory (conversation history stored in DB)
//   - Rich context: quick memory records, mode performance, study sessions
//   - Session logging via logSession()

import { useState, useCallback } from 'react'
import { z } from 'zod'
import { getGlobalLearningContext } from '../contexts/AIChatContext'
import type { AIMessage, LearningContext } from '../types'
import {
  safeParse,
  AIAskResponseSchema,
  AIPronunciationCheckResponseSchema,
  AIReviewPlanResponseSchema,
  AISpeakingSimulationResponseSchema,
  apiFetch,
  buildApiUrl,
} from '../lib'
import { ChapterProgressMapSchema } from '../lib/schemas'
import { STORAGE_KEYS } from '../constants'
import { readWrongWordsFromStorage } from '../features/vocabulary/wrongWordsStore'
import { readQuickMemoryRecordsFromStorage } from '../lib/quickMemory'

// ── localStorage schemas (permissive — extra keys ignored) ───────────────────
const ModePerformanceSchema = z.record(
  z.string(),
  z.object({ correct: z.number(), wrong: z.number() }).passthrough()
)
const WrongWordsSchema = z.array(z.record(z.string(), z.unknown()))
const SmartWordStatsSchema = z.record(
  z.string(),
  z.object({
    listening: z.object({ correct: z.number(), wrong: z.number() }),
    meaning:   z.object({ correct: z.number(), wrong: z.number() }),
    dictation: z.object({ correct: z.number(), wrong: z.number() }),
  }).passthrough()
)
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

interface UseAIChatOptions {
  userId?: string
}

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
export const STUDY_SESSION_IDLE_GRACE_MS = 20 * 60 * 1000
const REVIEW_PLAN_OPTION = '生成四维复习计划'
const START_SPEAKING_OPTION = '开始口语训练'
const CHANGE_SPEAKING_TASK_OPTION = '换一个口语任务'
const ANSWER_SPEAKING_TASK_OPTION = '我来回答这道题'
const CONTINUE_SPEAKING_OPTION = '我再补充一句'
const RETRY_PRONUNCIATION_OPTION = '再练一次这个词'

export interface GeneratedBook {
  bookId: string
  title: string
  description: string
  chapters: Array<{ id: string; title: string; wordCount: number }>
  words: Array<{
    chapterId: string
    word: string
    phonetic: string
    pos: string
    definition: string
  }>
}

interface PronunciationCommandPayload {
  word: string
  transcript: string
  sentence?: string
}

interface SpeakingCommandPayload {
  part: number
  topic: string
  targetWords: string[]
  responseText?: string
}

interface PendingPronunciationState {
  word: string
  awaitingInput: boolean
}

interface PendingSpeakingState {
  part: number
  topic: string
  targetWords: string[]
  awaitingResponse: boolean
}

function normalizeChapterId(value?: string | null): string | null {
  if (value == null) return null
  const text = String(value).trim()
  return text ? text : null
}

function normalizeCommandWords(value?: string | string[] | null): string[] {
  const rawValues = Array.isArray(value)
    ? value
    : typeof value === 'string'
      ? value.replace(/[，、]/g, ',').split(',')
      : []

  const seen = new Set<string>()
  const normalized: string[] = []
  for (const item of rawValues) {
    const word = String(item || '').trim()
    const key = word.toLowerCase()
    if (!key || seen.has(key)) continue
    seen.add(key)
    normalized.push(word)
  }
  return normalized
}

function normalizeFieldLabel(value: string): string {
  return value.trim().toLowerCase().replace(/\s+/g, '')
}

function hasEnglishText(value: string): boolean {
  return /[A-Za-z]/.test(value)
}

function parseLabeledBlocks(text: string): Record<string, string> {
  const lines = text.split(/\r?\n/)
  const fields: Record<string, string> = {}
  let activeKey: string | null = null
  let buffer: string[] = []

  const flush = () => {
    if (!activeKey) return
    fields[activeKey] = buffer.join('\n').trim()
  }

  for (const line of lines) {
    const match = line.match(/^\s*([A-Za-z\u4e00-\u9fa5 ]{1,20})[：:]\s*(.*)$/)
    if (match) {
      flush()
      activeKey = normalizeFieldLabel(match[1])
      buffer = [match[2]]
      continue
    }
    if (activeKey) {
      buffer.push(line)
    }
  }

  flush()
  return fields
}

function getFieldValue(fields: Record<string, string>, labels: string[]): string {
  for (const label of labels) {
    const value = fields[normalizeFieldLabel(label)]
    if (value) return value.trim()
  }
  return ''
}

function parsePronunciationCommand(input: string, context: LearningContext): PronunciationCommandPayload | null {
  const normalizedInput = input.trim()
  const isSlashCommand = /^\/pronounce\b/i.test(normalizedInput)
  const currentWord = String(context.currentWord || '').trim()
  if (isSlashCommand) {
    const remainder = normalizedInput.replace(/^\/pronounce\b/i, '').trim()
    if (!remainder) return null

    const parts = remainder.split('|').map(part => part.trim())
    if (parts.length === 1) {
      if (!currentWord) return null
      return {
        word: currentWord,
        transcript: parts[0],
      }
    }

    const [rawWord, transcript, sentence] = parts
    const word = rawWord || currentWord
    if (!word || !transcript) return null

    return {
      word,
      transcript,
      sentence: sentence || undefined,
    }
  }

  if (!/^(记录发音|发音记录)/.test(normalizedInput)) {
    return null
  }

  const fields = parseLabeledBlocks(normalizedInput)
  const word = getFieldValue(fields, ['单词', '目标词']) || currentWord
  const transcript = getFieldValue(fields, ['我的跟读', '跟读', '发音', '读音'])
  const sentence = getFieldValue(fields, ['我的例句', '例句', '造句'])
  if (!word || !transcript) return null

  return {
    word,
    transcript,
    sentence: sentence || undefined,
  }
}

function parseSpeakingCommand(input: string, context: LearningContext): SpeakingCommandPayload {
  const normalizedInput = input.trim()
  const currentWord = String(context.currentWord || '').trim()
  if (/^(开始口语训练|开始口语任务|给我一个口语任务|来一轮口语训练|换一个口语任务|换个口语题|再来一道口语题)$/.test(normalizedInput)) {
    return {
      part: 1,
      topic: 'education',
      targetWords: normalizeCommandWords(currentWord),
    }
  }

  if (/^(记录口语回答|我的口语回答)/.test(normalizedInput)) {
    const fields = parseLabeledBlocks(normalizedInput)
    const partValue = Number(getFieldValue(fields, ['part', 'Part', '部分']))
    const topicValue = getFieldValue(fields, ['主题', 'topic']) || 'education'
    const targetWords = normalizeCommandWords(
      getFieldValue(fields, ['目标词', '关键词']) || currentWord,
    )
    const responseText = getFieldValue(fields, ['我的回答', '回答'])
    return {
      part: [1, 2, 3].includes(partValue) ? partValue : 2,
      topic: topicValue,
      targetWords,
      responseText: responseText || undefined,
    }
  }

  const remainder = normalizedInput.replace(/^\/speaking\b/i, '').trim()
  const [headSegment, ...responseSegments] = remainder.split('|')
  const responseText = responseSegments.join('|').trim()
  let part = 1
  let topic = 'education'
  let targetWords = normalizeCommandWords(currentWord)
  let topicExplicit = false

  const head = headSegment.trim()
  if (head) {
    const looseTokens: string[] = []
    for (const token of head.split(/\s+/)) {
      if (!token) continue
      if (/^[123]$/.test(token)) {
        part = Number(token)
        continue
      }
      if (/^part=/i.test(token)) {
        const value = Number(token.split('=')[1])
        if ([1, 2, 3].includes(value)) part = value
        continue
      }
      if (/^topic=/i.test(token)) {
        const value = token.slice(token.indexOf('=') + 1).trim()
        if (value) {
          topic = value
          topicExplicit = true
        }
        continue
      }
      if (/^words=/i.test(token)) {
        const parsedWords = normalizeCommandWords(token.slice(token.indexOf('=') + 1))
        if (parsedWords.length > 0) targetWords = parsedWords
        continue
      }
      looseTokens.push(token)
    }

    if (!topicExplicit && looseTokens.length > 0) {
      topic = looseTokens.join(' ')
    }
  }

  if (targetWords.length === 0 && currentWord) {
    targetWords = [currentWord]
  }

  return {
    part,
    topic,
    targetWords,
    responseText: responseText || undefined,
  }
}

function buildPendingPronunciationPayload(
  input: string,
  pending: PendingPronunciationState,
): PronunciationCommandPayload | null {
  const normalizedInput = input.trim()
  if (!normalizedInput || !hasEnglishText(normalizedInput)) return null

  const explicitTranscript = normalizedInput.match(/(?:我读的是|我刚读的是|我跟读的是|我念的是)\s*[:：]?\s*([A-Za-z][A-Za-z' -]*)/i)
  const explicitSentence = normalizedInput.match(/(?:例句|句子|我造的句子|造句)(?:是)?\s*[:：]?\s*([\s\S]+)/)

  if (explicitTranscript) {
    return {
      word: pending.word,
      transcript: explicitTranscript[1].trim(),
      sentence: explicitSentence?.[1]?.trim() || undefined,
    }
  }

  if (explicitSentence) {
    return {
      word: pending.word,
      transcript: pending.word,
      sentence: explicitSentence[1].trim(),
    }
  }

  const tokenCount = normalizedInput.split(/\s+/).filter(Boolean).length
  if (tokenCount <= 4 && !/[.!?。！？]/.test(normalizedInput)) {
    return {
      word: pending.word,
      transcript: normalizedInput,
    }
  }

  if (normalizedInput.toLowerCase().includes(pending.word.toLowerCase())) {
    return {
      word: pending.word,
      transcript: pending.word,
      sentence: normalizedInput,
    }
  }

  return {
    word: pending.word,
    transcript: pending.word,
    sentence: normalizedInput,
  }
}

function buildPendingSpeakingPayload(
  input: string,
  pending: PendingSpeakingState,
): SpeakingCommandPayload | null {
  const normalizedInput = input.trim()
  if (!normalizedInput || !hasEnglishText(normalizedInput) || normalizedInput.length < 8) {
    return null
  }

  return {
    part: pending.part,
    topic: pending.topic,
    targetWords: pending.targetWords,
    responseText: normalizedInput,
  }
}

function readActiveStudySessionSnapshot(): ActiveStudySessionSnapshot | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEYS.ACTIVE_STUDY_SESSION)
    if (!raw) return null
    const parsed = safeParse(ActiveStudySessionSchema, JSON.parse(raw))
    return parsed.success ? parsed.data : null
  } catch {
    return null
  }
}

function writeActiveStudySessionSnapshot(snapshot: ActiveStudySessionSnapshot): void {
  localStorage.setItem(STORAGE_KEYS.ACTIVE_STUDY_SESSION, JSON.stringify(snapshot))
}

function clearActiveStudySessionSnapshot(sessionId?: number | null): void {
  if (!sessionId) {
    localStorage.removeItem(STORAGE_KEYS.ACTIVE_STUDY_SESSION)
    return
  }
  const snapshot = readActiveStudySessionSnapshot()
  if (!snapshot || snapshot.sessionId === sessionId) {
    localStorage.removeItem(STORAGE_KEYS.ACTIVE_STUDY_SESSION)
  }
}

function resolveSnapshotEndAt(snapshot: ActiveStudySessionSnapshot, now = Date.now()): number {
  const capped = snapshot.lastActiveAt + STUDY_SESSION_IDLE_GRACE_MS
  return Math.max(snapshot.startedAt, Math.min(now, capped))
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
  return {
    sessionId: data.sessionId,
    mode: data.mode ?? 'smart',
    bookId: data.bookId,
    chapterId: normalizeChapterId(data.chapterId),
    wordsStudied: Math.max(0, Math.round(data.wordsStudied || 0)),
    correctCount: Math.max(0, Math.round(data.correctCount || 0)),
    wrongCount: Math.max(0, Math.round(data.wrongCount || 0)),
    durationSeconds: Math.max(0, Math.round(data.durationSeconds || 0)),
    startedAt: Math.max(0, Math.round(data.startedAt || 0)),
    endedAt: data.endedAt != null ? Math.max(0, Math.round(data.endedAt)) : undefined,
  }
}

function shouldDiscardPassiveSession(payload: {
  wordsStudied: number
  correctCount: number
  wrongCount: number
  durationSeconds: number
}): boolean {
  return (
    payload.wordsStudied <= 0 &&
    payload.correctCount <= 0 &&
    payload.wrongCount <= 0 &&
    payload.durationSeconds < PASSIVE_STUDY_SESSION_MIN_SECONDS
  )
}

function sendStudySessionBeacon(url: string, payload: unknown): boolean {
  if (typeof navigator === 'undefined' || typeof navigator.sendBeacon !== 'function') {
    return false
  }
  try {
    const blob = new Blob([JSON.stringify(payload)], { type: 'application/json' })
    return navigator.sendBeacon(buildApiUrl(url), blob)
  } catch {
    return false
  }
}

function postStudySessionKeepalive(url: string, payload: unknown): void {
  void fetch(buildApiUrl(url), {
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

// ── Rich context builders ─────────────────────────────────────────────────────

function buildQuickMemorySummary() {
  try {
    const records = readQuickMemoryRecordsFromStorage()
    const now = Date.now()
    return Object.values(records).reduce(
      (acc, r) => {
        if (r.status === 'known') acc.known++
        else acc.unknown++
        if (r.nextReview && r.nextReview <= now) acc.dueToday++
        return acc
      },
      { known: 0, unknown: 0, dueToday: 0 },
    )
  } catch {
    return null
  }
}

function buildModePerformance() {
  try {
    const parsed = safeParse(ModePerformanceSchema, JSON.parse(localStorage.getItem('mode_performance') || '{}'))
    return parsed.success ? parsed.data : {}
  } catch {
    return {}
  }
}

// ── Session timer ─────────────────────────────────────────────────────────────

/**
 * Notify the server that a practice session has started.
 * Returns the server-assigned sessionId, or null on failure.
 * The server records started_at using its own clock, avoiding any client drift.
 */
/** 创建服务端会话行；请传入当前练习模式与词书上下文，避免仅 start-session 产生 mode 为空的记录 */
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

// ── Session logger ────────────────────────────────────────────────────────────

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
    // Non-critical
  }
}

export function updateStudySessionSnapshot(patch: SessionSnapshotPatch): void {
  const snapshot = readActiveStudySessionSnapshot()
  if (!snapshot) return
  if (patch.sessionId != null && patch.sessionId !== snapshot.sessionId) return

  const next: ActiveStudySessionSnapshot = {
    ...snapshot,
    mode: patch.mode ?? snapshot.mode,
    bookId: patch.bookId !== undefined ? (patch.bookId ?? null) : snapshot.bookId,
    chapterId: patch.chapterId !== undefined ? normalizeChapterId(patch.chapterId) : snapshot.chapterId,
    startedAt: patch.startedAt ?? snapshot.startedAt,
    lastActiveAt: Math.max(snapshot.lastActiveAt, patch.activeAt ?? Date.now()),
    wordsStudied: patch.wordsStudied ?? snapshot.wordsStudied,
    correctCount: patch.correctCount ?? snapshot.correctCount,
    wrongCount: patch.wrongCount ?? snapshot.wrongCount,
  }
  writeActiveStudySessionSnapshot(next)
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
  if (sessionId) {
    updateStudySessionSnapshot({
      sessionId,
      mode: data.mode,
      bookId: data.bookId,
      chapterId: data.chapterId,
      startedAt: data.startedAt,
      activeAt: endedAt,
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
    durationSeconds: Math.max(0, Math.round((endedAt - data.startedAt) / 1000)),
    startedAt: data.startedAt,
    endedAt,
  })

  if (sessionId) {
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
}

export async function logSession(data: {
  mode: string
  bookId?: string | null
  chapterId?: string | null
  wordsStudied: number
  correctCount: number
  wrongCount: number
  /** Used as fallback when sessionId is absent. */
  durationSeconds: number
  /** Epoch ms — fallback startedAt when sessionId is absent. */
  startedAt: number
  /** Server session ID from startSession(). When present the server computes duration. */
  sessionId?: number | null
  /** Epoch ms — lets the client recover an older session with a bounded end time. */
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
      activeAt: data.endedAt ?? Date.now(),
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
    .catch(() => { /* non-critical */ })
}

// ── Mode performance tracker (client-side localStorage) ──────────────────────

export function recordModeAnswer(mode: string, correct: boolean) {
  try {
    const parsed = safeParse(ModePerformanceSchema, JSON.parse(localStorage.getItem('mode_performance') || '{}'))
    const stored = parsed.success ? parsed.data : {}
    if (!stored[mode]) stored[mode] = { correct: 0, wrong: 0 }
    if (correct) stored[mode].correct++
    else stored[mode].wrong++
    localStorage.setItem('mode_performance', JSON.stringify(stored))
  } catch {
    // Non-critical
  }
}

type AIStreamEvent =
  | { type: 'status'; stage?: string; message?: string; tool?: string }
  | { type: 'text'; delta: string }
  | { type: 'options'; options: string[] }
  | { type: 'done'; reply: string; options?: string[] }
  | { type: 'error'; error?: string }

function resolveStreamStatusMessage(event: Extract<AIStreamEvent, { type: 'status' }>): string {
  const explicitMessage = event.message?.trim()
  if (explicitMessage) return explicitMessage
  if (event.stage === 'tool') {
    if (event.tool === 'web_search') return 'AI 正在检索相关资料...'
    if (event.tool === 'remember_user_note') return 'AI 正在记录你的学习信息...'
    if (event.tool === 'get_wrong_words') return 'AI 正在分析你的错词记录...'
    if (event.tool === 'get_chapter_words') return 'AI 正在读取章节词表...'
    if (event.tool === 'get_book_chapters') return 'AI 正在读取词书章节结构...'
    return 'AI 正在处理学习数据...'
  }
  return 'AI 正在思考...'
}

async function streamAIReply(params: {
  message: string
  context: LearningContext
  onEvent: (event: AIStreamEvent) => void | Promise<void>
}): Promise<void> {
  const response = await fetch(buildApiUrl('/api/ai/ask/stream'), {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
    },
    signal: AbortSignal.timeout(180_000),
    body: JSON.stringify({
      message: params.message,
      context: params.context,
    }),
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'AI 服务暂时不可用，请稍后重试' }))
    throw new Error(error.error || 'AI 服务暂时不可用，请稍后重试')
  }

  if (!response.body) {
    throw new Error('AI 响应流不可用')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let receivedDone = false

  const flushBuffer = async (force = false) => {
    while (true) {
      const match = buffer.match(/\r?\n\r?\n/)
      if (!match || match.index == null) break

      const rawEvent = buffer.slice(0, match.index)
      buffer = buffer.slice(match.index + match[0].length)

      const dataText = rawEvent
        .split(/\r?\n/)
        .filter(line => line.startsWith('data:'))
        .map(line => line.slice(5).trimStart())
        .join('\n')

      if (!dataText) continue
      const event = JSON.parse(dataText) as AIStreamEvent
      if (event.type === 'done') receivedDone = true
      await params.onEvent(event)
    }

    if (force && buffer.trim()) {
      const dataText = buffer
        .split(/\r?\n/)
        .filter(line => line.startsWith('data:'))
        .map(line => line.slice(5).trimStart())
        .join('\n')

      buffer = ''
      if (dataText) {
        const event = JSON.parse(dataText) as AIStreamEvent
        if (event.type === 'done') receivedDone = true
        await params.onEvent(event)
      }
    }
  }

  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    await flushBuffer()
  }

  buffer += decoder.decode()
  await flushBuffer(true)

  if (!receivedDone) {
    throw new Error('AI 响应中断，请稍后重试')
  }
}

// ── Main hook ─────────────────────────────────────────────────────────────────

export function useAIChat(_options: UseAIChatOptions = {}) {
  const [messages, setMessages] = useState<AIMessage[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [isGreeting, setIsGreeting] = useState(false)   // greeting in progress
  const [greetingDone, setGreetingDone] = useState(false) // greeting has completed (success or fail)
  const [error, setError] = useState<string | null>(null)
  const [isOpen, setIsOpen] = useState(false)
  const [contextLoaded, setContextLoaded] = useState(false)
  const [pendingPronunciation, setPendingPronunciation] = useState<PendingPronunciationState | null>(null)
  const [pendingSpeaking, setPendingSpeaking] = useState<PendingSpeakingState | null>(null)

  // Build the rich context object — merges global context (updated by PracticePage)
  // with local quick-memory, mode-performance, and historical chapter progress.
  const buildContext = useCallback(() => {
    // Parse chapter_progress (keyed as `{bookId}_{chapterId}` where chapterId is numeric)
    // and aggregate both per-book AND overall summaries for the AI.
    const chapterProgressSummary = (() => {
      try {
        const cParsed = safeParse(ChapterProgressMapSchema, JSON.parse(localStorage.getItem('chapter_progress') || '{}'))
        const raw = cParsed.success ? cParsed.data : {}
        const entries = Object.entries(raw)
        if (!entries.length) return undefined
        const completed = entries.filter(([, p]) => p.is_completed).length
        const totalCorrect = entries.reduce((s, [, p]) => s + (p.correct_count ?? 0), 0)
        const totalWrong = entries.reduce((s, [, p]) => s + (p.wrong_count ?? 0), 0)
        const totalAnswered = totalCorrect + totalWrong
        return {
          chaptersAttempted: entries.length,
          chaptersCompleted: completed,
          totalCorrect,
          totalWrong,
          overallAccuracy: totalAnswered > 0 ? Math.round(totalCorrect / totalAnswered * 100) : 0,
        }
      } catch { return undefined }
    })()

    // Per-book breakdown: group chapter_progress entries by bookId.
    // Key format: {bookId}_{chapterId} where chapterId is always an integer suffix.
    const localBookProgress = (() => {
      try {
        const cParsed = safeParse(ChapterProgressMapSchema, JSON.parse(localStorage.getItem('chapter_progress') || '{}'))
        const raw = cParsed.success ? cParsed.data : {}
        const bookMap: Record<string, { chaptersCompleted: number; chaptersAttempted: number; correct: number; wrong: number; wordsLearned: number }> = {}

        for (const [key, data] of Object.entries(raw)) {
          // Split off trailing numeric chapterId: "ielts_listening_premium_3" → bookId="ielts_listening_premium"
          const match = key.match(/^(.+)_(\d+)$/)
          if (!match) continue
          const bookId = match[1]
          if (!bookMap[bookId]) bookMap[bookId] = { chaptersCompleted: 0, chaptersAttempted: 0, correct: 0, wrong: 0, wordsLearned: 0 }
          bookMap[bookId].chaptersAttempted++
          if (data.is_completed) bookMap[bookId].chaptersCompleted++
          bookMap[bookId].correct += data.correct_count ?? 0
          bookMap[bookId].wrong += data.wrong_count ?? 0
          bookMap[bookId].wordsLearned += data.words_learned ?? 0
        }

        // Merge in book-level progress (correct/wrong totals at book scope)
        try {
          const BookProgressSchema = z.record(z.string(), z.object({
            correct_count: z.number().optional(),
            wrong_count: z.number().optional(),
            is_completed: z.boolean().optional(),
          }).passthrough())
          const bParsed = safeParse(BookProgressSchema, JSON.parse(localStorage.getItem('book_progress') || '{}'))
          if (bParsed.success) {
            for (const [bookId, bp] of Object.entries(bParsed.data)) {
              if (!bookMap[bookId]) bookMap[bookId] = { chaptersCompleted: 0, chaptersAttempted: 0, correct: 0, wrong: 0, wordsLearned: 0 }
              // Only use book-level stats if chapter-level stats are absent
              if (bookMap[bookId].chaptersAttempted === 0) {
                bookMap[bookId].correct = bp.correct_count ?? 0
                bookMap[bookId].wrong = bp.wrong_count ?? 0
              }
            }
          }
        } catch { /* ignore */ }

        return Object.keys(bookMap).length > 0 ? bookMap : null
      } catch { return null }
    })()

    return {
      ...getGlobalLearningContext(),
      quickMemorySummary: buildQuickMemorySummary(),
      modePerformance: buildModePerformance(),
      localHistory: chapterProgressSummary,
      localBookProgress,
    }
  }, [])

  const _syncWrongWords = useCallback(async () => {
    try {
      const wwParsed = safeParse(WrongWordsSchema, readWrongWordsFromStorage())
      const wrongWords = wwParsed.success ? wwParsed.data : []
      if (!wrongWords.length) return
      const ssParsed = safeParse(SmartWordStatsSchema, JSON.parse(localStorage.getItem(STORAGE_KEYS.SMART_WORD_STATS) || '{}'))
      const smartStats = ssParsed.success ? ssParsed.data : {}
      const enriched = wrongWords.map(w => {
        const ws = smartStats[w.word as string]
        return {
          ...w,
          listeningCorrect: ws?.listening.correct ?? 0,
          listeningWrong:   ws?.listening.wrong   ?? 0,
          meaningCorrect:   ws?.meaning.correct   ?? 0,
          meaningWrong:     ws?.meaning.wrong     ?? 0,
          dictationCorrect: ws?.dictation.correct ?? 0,
          dictationWrong:   ws?.dictation.wrong   ?? 0,
        }
      })
      await apiFetch('/api/ai/wrong-words/sync', {
        method: 'POST',
        body: JSON.stringify({ words: enriched }),
      })
    } catch {
      // Non-critical
    }
  }, [])

  const _fetchGreeting = useCallback(async () => {
    setIsGreeting(true)
    try {
      const raw = await apiFetch('/api/ai/greet', {
        method: 'POST',
        body: JSON.stringify({ context: buildContext() }),
      })
      const result = safeParse(AIAskResponseSchema, raw)
      const content = result.success
        ? result.data.reply
        : '你好！我是雅思小助手，有什么我可以帮你的吗？'
      const options = (result.success && result.data.options) ? result.data.options : undefined
      setMessages([{
        id: 'greet',
        role: 'assistant',
        content,
        options: options ?? undefined,
        timestamp: Date.now(),
      }])
    } catch {
      setMessages([{
        id: 'greet',
        role: 'assistant',
        content: '你好！我是雅思小助手 👋\n\n我可以帮你分析学习进度、找出薄弱单词、制定复习计划，或者生成专属词书。有什么我可以帮你的吗？',
        timestamp: Date.now(),
      }])
    } finally {
      setIsGreeting(false)
      setGreetingDone(true)
    }
  }, [buildContext])

  const openPanel = useCallback(async () => {
    setIsOpen(true)
    if (contextLoaded) return
    setContextLoaded(true)
    await _syncWrongWords()
    await _fetchGreeting()
  }, [contextLoaded, _syncWrongWords, _fetchGreeting])

  const closePanel = useCallback(() => setIsOpen(false), [])

  const sendMessage = useCallback(async (text: string) => {
    const userMsg: AIMessage = {
      id: `user_${Date.now()}`,
      role: 'user',
      content: text,
      timestamp: Date.now(),
    }
    setMessages(prev => [...prev, userMsg])
    setIsLoading(true)
    setError(null)
    let streamingAssistantId: string | null = null
    let streamedContent = ''

    try {
      const normalized = text.trim()
      const context = buildContext() as LearningContext
      const correctionMatch = normalized.match(/^(?:\/correct\s+|帮我纠正这句话[：:]?\s*|纠正这句话[：:]?\s*)([\s\S]+)$/)
      const exampleMatch = normalized.match(/^给我\s+(.+?)\s+的(?:真题)?例句$/)
      const synonymsMatch = normalized.match(/^辨析\s+(.+?)\s+(?:和|vs)\s+(.+)$/i)
      const familyMatch = normalized.match(/^查看\s+(.+?)\s+的词族$/)
      const wantsCollocation = normalized === '开始搭配训练'
      const wantsPlan = /^(生成四维复习计划|生成复习计划|查看复习计划)$/.test(normalized)
      const wantsAssessment = /^(开始词汇量评估|做词汇量评估)$/.test(normalized)
      const appendAssistantMessage = (content: string, options?: string[]) => {
        setMessages(prev => [...prev, {
          id: `asst_${Date.now()}`,
          role: 'assistant',
          content,
          options: options ?? undefined,
          timestamp: Date.now(),
        }])
      }
      const createStreamingAssistantMessage = () => {
        const id = `asst_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
        setMessages(prev => [...prev, {
          id,
          role: 'assistant',
          content: '',
          isStreaming: true,
          timestamp: Date.now(),
        }])
        return id
      }
      const updateAssistantMessage = (id: string, patch: Partial<AIMessage>) => {
        setMessages(prev => prev.map(message => (
          message.id === id
            ? { ...message, ...patch }
            : message
        )))
      }
      const pausePendingFlows = () => {
        setPendingPronunciation(prev => (prev ? { ...prev, awaitingInput: false } : null))
        setPendingSpeaking(prev => (prev ? { ...prev, awaitingResponse: false } : null))
      }
      const startPronunciationFlow = () => {
        const currentWord = String(context.currentWord || '').trim()
        const word = pendingPronunciation?.word || currentWord
        if (!word) {
          appendAssistantMessage(
            '先打开一个正在学习的单词，我就能按当前词带你练发音。你也可以先做一轮口语任务。',
            [START_SPEAKING_OPTION, REVIEW_PLAN_OPTION],
          )
          return
        }
        setPendingPronunciation({ word, awaitingInput: true })
        setPendingSpeaking(prev => (prev ? { ...prev, awaitingResponse: false } : null))
        appendAssistantMessage(
          `我们先练 ${word}。直接回复你刚才读出来的英文就行；如果你愿意，也可以直接发一句包含 ${word} 的英文句子，我会一起记入口语证据。`,
          [START_SPEAKING_OPTION, REVIEW_PLAN_OPTION],
        )
      }
      const promptSpeakingReply = () => {
        if (!pendingSpeaking) {
          appendAssistantMessage(
            '先给你一道口语题，再直接回答会更顺畅。',
            [START_SPEAKING_OPTION, REVIEW_PLAN_OPTION],
          )
          return
        }
        const targetWordsText = pendingSpeaking.targetWords.length > 0
          ? `，尽量带上 ${pendingSpeaking.targetWords.join('、')}`
          : ''
        setPendingSpeaking(prev => (prev ? { ...prev, awaitingResponse: true } : null))
        setPendingPronunciation(prev => (prev ? { ...prev, awaitingInput: false } : null))
        appendAssistantMessage(
          `直接回复你的英文回答就行，我会按刚才这道题继续记录口语证据${targetWordsText}。`,
          [CHANGE_SPEAKING_TASK_OPTION, REVIEW_PLAN_OPTION],
        )
      }

      const pronunciationPayload = parsePronunciationCommand(normalized, context)
      const pronunciationFollowUpPayload = pendingPronunciation?.awaitingInput
        ? buildPendingPronunciationPayload(normalized, pendingPronunciation)
        : null
      const speakingFollowUpPayload = pendingSpeaking?.awaitingResponse
        ? buildPendingSpeakingPayload(normalized, pendingSpeaking)
        : null
      const wantsPronunciationStart = /^(开始发音训练|练这个词的发音|帮我检查发音|检查这个词的发音|我来跟读这个词|再练一次这个词)$/.test(normalized)
      const wantsSpeakingReply = /^(我来回答这道题|我再补充一句)$/.test(normalized)
      const wantsPronunciation = pronunciationPayload !== null
        || pronunciationFollowUpPayload !== null
        || /^\/pronounce\b/i.test(normalized)
        || /^(记录发音|发音记录)/.test(normalized)
      const wantsSpeaking = /^\/speaking\b/i.test(normalized)
        || speakingFollowUpPayload !== null
        || /^(开始口语训练|开始口语任务|给我一个口语任务|来一轮口语训练|换一个口语任务|换个口语题|再来一道口语题|记录口语回答|我的口语回答)/.test(normalized)

      if (wantsPronunciationStart) {
        startPronunciationFlow()
        return
      }
      if (wantsSpeakingReply) {
        promptSpeakingReply()
        return
      }
      if (correctionMatch) {
        pausePendingFlows()
        const sentence = correctionMatch[1].trim()
        const result = await apiFetch<Record<string, unknown>>('/api/ai/correct-text', {
          method: 'POST',
          body: JSON.stringify({ text: sentence }),
        })
        const upgrades = Array.isArray(result.upgrades) ? result.upgrades as Array<Record<string, string>> : []
        const collocations = Array.isArray(result.collocations) ? result.collocations as Array<Record<string, string>> : []
        const lines = [
          '写作纠错结果：',
          `- 语法：${result.grammar_ok ? '基本正确' : '建议优化'}`,
          `- 修正句：${String(result.corrected_sentence || sentence)}`,
        ]
        if (upgrades.length) {
          lines.push('- 词汇升级：')
          upgrades.slice(0, 3).forEach((u) => lines.push(`  ${u.from} -> ${u.to}（${u.reason || '提升学术表达'}）`))
        }
        if (collocations.length) {
          lines.push('- 搭配建议：')
          collocations.slice(0, 3).forEach((c) => lines.push(`  ${c.wrong} -> ${c.right}`))
        }
        lines.push(String(result.encouragement || '继续保持，建议多练 Task 2 学术表达。'))
        appendAssistantMessage(lines.join('\n'))
        return
      }
      if (exampleMatch || normalized.startsWith('/example ')) {
        pausePendingFlows()
        const word = exampleMatch?.[1]?.trim() || normalized.replace('/example ', '').trim()
        const result = await apiFetch<{ examples: Array<{ sentence: string; source?: string }> }>(`/api/ai/ielts-example?word=${encodeURIComponent(word)}`)
        const lines = ['真题语境例句：', ...result.examples.slice(0, 3).map((e, i) => `${i + 1}. ${e.sentence} (${e.source || 'unknown'})`)]
        appendAssistantMessage(lines.join('\n'))
        return
      }
      if (synonymsMatch || normalized.startsWith('/synonyms ')) {
        pausePendingFlows()
        const pair = synonymsMatch
          ? [synonymsMatch[1].trim(), synonymsMatch[2].trim()]
          : normalized.replace('/synonyms ', '').split(/\s+vs\s+|\s+/i)
        const [a, b] = pair
        const result = await apiFetch<{ summary: string; quiz?: { question?: string } }>('/api/ai/synonyms-diff', {
          method: 'POST',
          body: JSON.stringify({ a, b }),
        })
        appendAssistantMessage(`${result.summary}\n${result.quiz?.question || ''}`.trim())
        return
      }
      if (familyMatch || normalized.startsWith('/family ')) {
        pausePendingFlows()
        const word = familyMatch?.[1]?.trim() || normalized.replace('/family ', '').trim()
        const result = await apiFetch<Record<string, unknown>>(`/api/ai/word-family?word=${encodeURIComponent(word)}`)
        const variants = (result.variants as Array<Record<string, string>> | undefined) || []
        const textOut = variants.length
          ? `词族树 ${word}：\n${variants.map(v => `- ${v.word} (${v.pos})`).join('\n')}`
          : String(result.message || '暂无词族数据')
        appendAssistantMessage(textOut)
        return
      }
      if (wantsCollocation || normalized.startsWith('/collocation')) {
        pausePendingFlows()
        const result = await apiFetch<{ items: Array<{ wrong: string; right: string; explanation: string }> }>('/api/ai/collocations/practice?count=5')
        const textOut = `搭配训练：\n${result.items.map(i => `- ${i.wrong} -> ${i.right}（${i.explanation}）`).join('\n')}`
        appendAssistantMessage(textOut)
        return
      }
      if (wantsPronunciation) {
        const payload = pronunciationPayload ?? pronunciationFollowUpPayload
        if (!payload) {
          startPronunciationFlow()
          return
        }

        const raw = await apiFetch('/api/ai/pronunciation-check', {
          method: 'POST',
          body: JSON.stringify({
            ...payload,
            bookId: context.currentBook,
            chapterId: context.currentChapter,
          }),
        })
        const result = safeParse(AIPronunciationCheckResponseSchema, raw)
        if (!result.success) {
          throw new Error('发音检查响应格式错误')
        }
        setPendingPronunciation({ word: result.data.word, awaitingInput: false })
        setPendingSpeaking(prev => (prev ? { ...prev, awaitingResponse: false } : null))

        const lines = [
          `发音检查：${result.data.word}`,
          `- 分数：${Math.round(result.data.score)}`,
          `- 结果：${result.data.passed ? '通过' : '待强化'}`,
          `- 重音：${result.data.stress_feedback}`,
          `- 元音：${result.data.vowel_feedback}`,
          `- 节奏：${result.data.speed_feedback}`,
        ]
        if (payload.sentence) {
          lines.push(`- 已记录：发音 + 造句证据`)
        } else {
          lines.push('- 已记录：发音证据；再补一句英文句子就能补全口语输出证据。')
        }
        appendAssistantMessage(lines.join('\n'), [
          RETRY_PRONUNCIATION_OPTION,
          START_SPEAKING_OPTION,
          REVIEW_PLAN_OPTION,
        ])
        return
      }
      if (wantsPlan || normalized.startsWith('/plan')) {
        pausePendingFlows()
        const raw = await apiFetch('/api/ai/review-plan')
        const result = safeParse(AIReviewPlanResponseSchema, raw)
        if (!result.success) {
          throw new Error('复习计划响应格式错误')
        }
        const lines = [`今日复习计划（${result.data.level}）：`]
        if (result.data.mastery_rule) lines.push(result.data.mastery_rule)
        if (result.data.priority_dimension) {
          const reason = result.data.priority_reason ? `，原因：${result.data.priority_reason}` : ''
          lines.push(`当前优先维度：${result.data.priority_dimension}${reason}`)
        }
        if (Array.isArray(result.data.dimensions) && result.data.dimensions.length > 0) {
          lines.push('四维安排：')
          result.data.dimensions.forEach((item) => {
            const label = item.label || '维度'
            const status = item.status_label || '待安排'
            const schedule = item.schedule_label ? `，周期 ${item.schedule_label}` : ''
            lines.push(`- ${label}：${status}${schedule}`)
          })
        }
        if (result.data.plan.length > 0) {
          lines.push('建议动作：')
          lines.push(...result.data.plan.map(item => `- ${item}`))
        }
        appendAssistantMessage(lines.join('\n'))
        return
      }
      if (wantsAssessment || normalized.startsWith('/assessment')) {
        pausePendingFlows()
        const result = await apiFetch<{ questions: Array<{ word: string; definition: string }> }>('/api/ai/vocab-assessment?count=10')
        const preview = result.questions.slice(0, 5).map((q, idx) => `${idx + 1}. ${q.word}: ${q.definition}`).join('\n')
        appendAssistantMessage(`词汇量评估（预览）：\n${preview}`)
        return
      }
      if (wantsSpeaking) {
        const payload = speakingFollowUpPayload ?? parseSpeakingCommand(normalized, context)
        const raw = await apiFetch('/api/ai/speaking-simulate', {
          method: 'POST',
          body: JSON.stringify({
            part: payload.part,
            topic: payload.topic,
            targetWords: payload.targetWords,
            responseText: payload.responseText,
            bookId: context.currentBook,
            chapterId: context.currentChapter,
          }),
        })
        const result = safeParse(AISpeakingSimulationResponseSchema, raw)
        if (!result.success) {
          throw new Error('口语任务响应格式错误')
        }
        setPendingPronunciation(prev => (prev ? { ...prev, awaitingInput: false } : null))
        setPendingSpeaking({
          part: result.data.part,
          topic: result.data.topic,
          targetWords: payload.targetWords,
          awaitingResponse: !payload.responseText,
        })

        const lines = [
          `口语任务（Part ${result.data.part} / ${result.data.topic}）：`,
          result.data.question,
        ]
        if (payload.targetWords.length > 0) {
          lines.push(`目标词：${payload.targetWords.join('、')}`)
        }
        if (payload.responseText) {
          lines.push('已记录你的回答，口语维度会按 1/3/7/15/30 天节点继续安排复现。')
        } else {
          lines.push('直接回复你的英文回答就行，我会按这道题继续记录口语证据。')
        }
        if (result.data.follow_ups.length > 0) {
          lines.push('追问方向：')
          lines.push(...result.data.follow_ups.map(item => `- ${item}`))
        }
        appendAssistantMessage(
          lines.join('\n'),
          payload.responseText
            ? [CONTINUE_SPEAKING_OPTION, CHANGE_SPEAKING_TASK_OPTION, REVIEW_PLAN_OPTION]
            : [ANSWER_SPEAKING_TASK_OPTION, CHANGE_SPEAKING_TASK_OPTION, REVIEW_PLAN_OPTION],
        )
        return
      }

      pausePendingFlows()
      streamingAssistantId = createStreamingAssistantMessage()
      let streamedOptions: string[] | undefined

      await streamAIReply({
        message: text,
        context,
        onEvent: (event) => {
          if (!streamingAssistantId) return

          if (event.type === 'status') {
            if (!streamedContent.trim()) {
              updateAssistantMessage(streamingAssistantId, {
                content: resolveStreamStatusMessage(event),
                isStreaming: true,
              })
            }
            return
          }

          if (event.type === 'text') {
            streamedContent += event.delta
            updateAssistantMessage(streamingAssistantId, {
              content: streamedContent,
              isStreaming: true,
            })
            return
          }

          if (event.type === 'options') {
            streamedOptions = event.options
            updateAssistantMessage(streamingAssistantId, {
              options: event.options,
              isStreaming: true,
            })
            return
          }

          if (event.type === 'done') {
            streamedContent = event.reply
            streamedOptions = event.options ?? streamedOptions
            updateAssistantMessage(streamingAssistantId, {
              content: event.reply,
              options: streamedOptions,
              isStreaming: false,
            })
            return
          }

          if (event.type === 'error') {
            throw new Error(event.error || 'AI 服务暂时不可用，请稍后重试')
          }
        },
      })
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : '未知错误'
      setError(msg)
      if (streamingAssistantId) {
        if (streamedContent.trim()) {
          setMessages(prev => prev.map(message => (
            message.id === streamingAssistantId
              ? { ...message, content: streamedContent, isStreaming: false }
              : message
          )))
        } else {
          setMessages(prev => prev.filter(message => message.id !== streamingAssistantId))
        }
      }
      setMessages(prev => [...prev, {
        id: `err_${Date.now()}`,
        role: 'assistant',
        content: `出错了：${msg}`,
        timestamp: Date.now(),
      }])
    } finally {
      setIsLoading(false)
    }
  }, [buildContext, pendingPronunciation, pendingSpeaking])

  return {
    messages,
    isLoading,
    isGreeting,
    greetingDone,
    error,
    isOpen,
    contextLoaded,
    openPanel,
    closePanel,
    sendMessage,
  }
}
