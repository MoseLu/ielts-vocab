import { buildPracticeIdempotencyKey } from './commandKeys'
import { buildLearningScope } from '../learningScope'
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

export function buildPracticeResultCommand(input: BuildPracticeResultCommandInput): PracticeResultCommand {
  const contract = getPracticeModeContract(input.mode)
  const sessionId = input.session?.sessionId ?? null
  const localSessionId = input.session?.localSessionId ?? `${input.mode}:${input.route}`
  const scope = buildLearningScope(input.progressScope)
  return {
    traceId: normalizePracticeTraceId(input.traceId),
    idempotencyKey: buildPracticeIdempotencyKey({
      sessionId,
      localSessionId,
      mode: input.mode,
      scopeKey: scope.scopeKey,
      wordKey: input.word,
      dimension: input.dimension,
      attemptIndex: input.attemptIndex ?? 0,
    }),
    userScope: String(input.userScope),
    route: input.route,
    mode: input.mode,
    scopeKey: scope.scopeKey,
    scopeType: scope.scopeType,
    originScope: scope.originScope,
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
