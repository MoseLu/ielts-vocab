import type { PracticeResultCommand } from './types'
import { setStorageJsonSafely } from '../storage'

export type PracticeResultOutboxStatus = 'pending' | 'sending' | 'acked' | 'failed'

export interface PracticeResultOutboxEntry {
  idempotencyKey: string
  status: PracticeResultOutboxStatus
  command: PracticeResultCommand
  attempts: number
  createdAt: number
  updatedAt: number
  nextRetryAt?: number
  lastError?: string
}

const OUTBOX_KEY_PREFIX = 'practice_result_outbox:user:'
const DEFAULT_RETRY_DELAY_MS = 1_000
const MAX_ACTIVE_OUTBOX_ENTRIES = 60
const MAX_ACKED_OUTBOX_ENTRIES = 20
const QUOTA_FALLBACK_ACTIVE_ENTRIES = 20

export function getPracticeResultOutboxStorageKey(userScope: string | number): string {
  return `${OUTBOX_KEY_PREFIX}${String(userScope)}`
}

function readEntries(userScope: string): PracticeResultOutboxEntry[] {
  try {
    const raw = JSON.parse(localStorage.getItem(getPracticeResultOutboxStorageKey(userScope)) || '[]')
    return Array.isArray(raw)
      ? raw.filter(entry => entry && typeof entry === 'object' && typeof entry.idempotencyKey === 'string')
      : []
  } catch {
    return []
  }
}

function newestFirst(entries: PracticeResultOutboxEntry[]): PracticeResultOutboxEntry[] {
  return [...entries].sort((left, right) => right.updatedAt - left.updatedAt)
}

function compactEntries(
  entries: PracticeResultOutboxEntry[],
  activeLimit = MAX_ACTIVE_OUTBOX_ENTRIES,
  ackedLimit = MAX_ACKED_OUTBOX_ENTRIES,
): PracticeResultOutboxEntry[] {
  const active = newestFirst(entries.filter(entry => entry.status !== 'acked')).slice(0, activeLimit)
  const acked = newestFirst(entries.filter(entry => entry.status === 'acked')).slice(0, ackedLimit)
  return [...active, ...acked].sort((left, right) => left.createdAt - right.createdAt)
}

function writeEntries(userScope: string, entries: PracticeResultOutboxEntry[]): void {
  const storageKey = getPracticeResultOutboxStorageKey(userScope)
  const compacted = compactEntries(entries)
  if (setStorageJsonSafely(storageKey, compacted)) return

  setStorageJsonSafely(storageKey, compactEntries(entries, QUOTA_FALLBACK_ACTIVE_ENTRIES, 0))
}

function upsertEntry(
  userScope: string,
  idempotencyKey: string,
  update: (entry: PracticeResultOutboxEntry | null, now: number) => PracticeResultOutboxEntry,
): PracticeResultOutboxEntry {
  const entries = readEntries(userScope)
  const existingIndex = entries.findIndex(entry => entry.idempotencyKey === idempotencyKey)
  const now = Date.now()
  const nextEntry = update(existingIndex >= 0 ? entries[existingIndex] : null, now)
  if (existingIndex >= 0) entries[existingIndex] = nextEntry
  else entries.push(nextEntry)
  writeEntries(userScope, entries)
  return nextEntry
}

export function readPracticeResultOutbox(userScope: string): PracticeResultOutboxEntry[] {
  return readEntries(userScope)
}

export function enqueuePracticeResultCommand(command: PracticeResultCommand): PracticeResultOutboxEntry {
  return upsertEntry(command.userScope, command.idempotencyKey, (entry, now) => {
    if (entry && entry.status === 'acked') return entry
    return {
      idempotencyKey: command.idempotencyKey,
      status: entry?.status === 'sending' ? 'sending' : 'pending',
      command,
      attempts: entry?.attempts ?? 0,
      createdAt: entry?.createdAt ?? now,
      updatedAt: now,
      nextRetryAt: entry?.nextRetryAt,
      lastError: entry?.lastError,
    }
  })
}

export function markPracticeResultSending(command: PracticeResultCommand): PracticeResultOutboxEntry {
  return upsertEntry(command.userScope, command.idempotencyKey, (entry, now) => ({
    idempotencyKey: command.idempotencyKey,
    status: 'sending',
    command,
    attempts: (entry?.attempts ?? 0) + 1,
    createdAt: entry?.createdAt ?? now,
    updatedAt: now,
  }))
}

export function markPracticeResultAcked(command: PracticeResultCommand): PracticeResultOutboxEntry {
  return upsertEntry(command.userScope, command.idempotencyKey, (entry, now) => ({
    idempotencyKey: command.idempotencyKey,
    status: 'acked',
    command,
    attempts: entry?.attempts ?? 0,
    createdAt: entry?.createdAt ?? now,
    updatedAt: now,
  }))
}

export function markPracticeResultFailed(
  command: PracticeResultCommand,
  error: string,
  retryDelayMs = DEFAULT_RETRY_DELAY_MS,
): PracticeResultOutboxEntry {
  return upsertEntry(command.userScope, command.idempotencyKey, (entry, now) => ({
    idempotencyKey: command.idempotencyKey,
    status: 'failed',
    command,
    attempts: entry?.attempts ?? 0,
    createdAt: entry?.createdAt ?? now,
    updatedAt: now,
    nextRetryAt: now + Math.max(DEFAULT_RETRY_DELAY_MS, retryDelayMs),
    lastError: error,
  }))
}

export function listRetryablePracticeResults(
  userScope: string,
  now = Date.now(),
): PracticeResultOutboxEntry[] {
  return readEntries(userScope).filter(entry => (
    entry.status === 'pending'
    || (entry.status === 'failed' && (entry.nextRetryAt ?? 0) <= now)
  ))
}

export function pruneAckedPracticeResults(
  userScope: string,
  maxAgeMs: number,
  now = Date.now(),
): number {
  const entries = readEntries(userScope)
  const retained = entries.filter(entry => (
    entry.status !== 'acked'
    || now - entry.updatedAt < maxAgeMs
  ))
  writeEntries(userScope, retained)
  return entries.length - retained.length
}
