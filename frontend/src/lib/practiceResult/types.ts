import type {
  PracticeResultPlane,
  PracticeRuntimeId,
} from './modeContracts'

export type PracticeResultOutcome = 'correct' | 'wrong' | 'known' | 'unknown' | 'skipped'

export interface PracticeResultSessionScope {
  sessionId?: number | null
  localSessionId?: string | null
}

export interface PracticeResultProgressScope {
  bookId?: string | null
  chapterId?: string | number | null
  day?: number | null
}

export interface PracticeResultCommand {
  traceId: string
  idempotencyKey: string
  userScope: string
  route: string
  mode: PracticeRuntimeId
  dimension: string
  word: string
  wordPayload?: Record<string, unknown> | null
  result: PracticeResultOutcome
  occurredAt: number
  session?: PracticeResultSessionScope
  progressScope?: PracticeResultProgressScope
  adapter: string
}

export type PracticeResultPlaneStatus = 'ok' | 'skipped' | 'failed'

export interface PracticeResultPlaneOutcome {
  plane: PracticeResultPlane
  status: PracticeResultPlaneStatus
  error?: string
}

export interface PracticeResultApplyResult {
  traceId: string
  idempotencyKey: string
  planes: PracticeResultPlaneOutcome[]
}

export type PracticeResultPlaneHandler = (
  command: PracticeResultCommand,
  plane: PracticeResultPlane,
) => void | Promise<void>

export type PracticeResultPlaneHandlers = Partial<Record<PracticeResultPlane, PracticeResultPlaneHandler>>
