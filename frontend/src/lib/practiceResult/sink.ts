import { getPracticeModeContract } from './modeContracts'
import {
  enqueuePracticeResultCommand,
  markPracticeResultAcked,
  markPracticeResultFailed,
  markPracticeResultSending,
} from './outbox'
import type {
  PracticeResultApplyResult,
  PracticeResultCommand,
  PracticeResultPlaneHandler,
  PracticeResultPlaneHandlers,
  PracticeResultPlaneOutcome,
} from './types'

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error || 'unknown error')
}

async function applyPlane(
  command: PracticeResultCommand,
  plane: PracticeResultPlaneOutcome['plane'],
  handler?: PracticeResultPlaneHandler,
): Promise<PracticeResultPlaneOutcome> {
  if (!handler) return { plane, status: 'skipped' }
  try {
    await handler(command, plane)
    return { plane, status: 'ok' }
  } catch (error) {
    return { plane, status: 'failed', error: errorMessage(error) }
  }
}

export async function applyPracticeResult(
  command: PracticeResultCommand,
  handlers: PracticeResultPlaneHandlers,
): Promise<PracticeResultApplyResult> {
  enqueuePracticeResultCommand(command)
  markPracticeResultSending(command)

  const contract = getPracticeModeContract(command.mode)
  const planes: PracticeResultPlaneOutcome[] = []
  for (const plane of contract.writes) {
    planes.push(await applyPlane(command, plane, handlers[plane]))
  }

  const failedPlane = planes.find(plane => plane.status === 'failed')
  if (failedPlane) {
    markPracticeResultFailed(command, failedPlane.error ?? 'practice result plane failed')
  } else {
    markPracticeResultAcked(command)
  }

  return {
    traceId: command.traceId,
    idempotencyKey: command.idempotencyKey,
    planes,
  }
}
