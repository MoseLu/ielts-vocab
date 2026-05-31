export type ManagedAudioFailureReason = 'not-allowed' | 'unknown'

let lastManagedAudioFailureReason: ManagedAudioFailureReason | null = null

export function rememberManagedAudioFailureReason(reason: ManagedAudioFailureReason | null): void {
  lastManagedAudioFailureReason = reason
}

export function consumeManagedAudioFailureReason(): ManagedAudioFailureReason | null {
  const reason = lastManagedAudioFailureReason
  lastManagedAudioFailureReason = null
  return reason
}

export function resetManagedAudioFailureReason(): void {
  lastManagedAudioFailureReason = null
}

export function getManagedAudioFailureReason(): ManagedAudioFailureReason | null {
  return lastManagedAudioFailureReason
}

export function isAutoplayBlockedError(error: unknown): boolean {
  return error instanceof Error && error.name === 'NotAllowedError'
}
