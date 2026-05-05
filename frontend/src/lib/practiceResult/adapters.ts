import { buildPracticeIdempotencyKey } from './commandKeys'
import { getPracticeModeContract, type PracticeRuntimeId } from './modeContracts'
import { normalizePracticeTraceId } from './trace'
import type {
  PracticeResultCommand,
  PracticeResultOutcome,
  PracticeResultProgressScope,
  PracticeResultSessionScope,
} from './types'

interface BuildPracticeResultCommandInput {
  traceId?: string | null
  userScope: string | number
  route: string
  mode: PracticeRuntimeId
  dimension: string
  word: string
  wordPayload?: Record<string, unknown> | null
  result: PracticeResultOutcome
  occurredAt?: number
  session?: PracticeResultSessionScope
  progressScope?: PracticeResultProgressScope
  adapter?: string
  attemptIndex?: number
}

function scopeKey(progressScope: PracticeResultProgressScope | undefined): string {
  if (!progressScope) return 'global'
  if (progressScope.bookId && progressScope.chapterId != null) {
    return `${progressScope.bookId}:chapter:${progressScope.chapterId}`
  }
  if (progressScope.bookId) return `${progressScope.bookId}:book`
  if (progressScope.day != null) return `day:${progressScope.day}`
  return 'global'
}

export function buildPracticeResultCommand(input: BuildPracticeResultCommandInput): PracticeResultCommand {
  const contract = getPracticeModeContract(input.mode)
  const sessionId = input.session?.sessionId ?? null
  const localSessionId = input.session?.localSessionId ?? `${input.mode}:${input.route}`
  return {
    traceId: normalizePracticeTraceId(input.traceId),
    idempotencyKey: buildPracticeIdempotencyKey({
      sessionId,
      localSessionId,
      mode: input.mode,
      scopeKey: scopeKey(input.progressScope),
      wordKey: input.word,
      dimension: input.dimension,
      attemptIndex: input.attemptIndex ?? 0,
    }),
    userScope: String(input.userScope),
    route: input.route,
    mode: input.mode,
    dimension: input.dimension,
    word: input.word,
    wordPayload: input.wordPayload,
    result: input.result,
    occurredAt: input.occurredAt ?? Date.now(),
    session: input.session,
    progressScope: input.progressScope,
    adapter: input.adapter ?? contract.runtimeKind,
  }
}
