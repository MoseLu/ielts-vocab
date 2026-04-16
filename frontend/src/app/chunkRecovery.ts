const CHUNK_RELOAD_MARKER = '__vite_chunk_reload_at__'
const CHUNK_RELOAD_WINDOW_MS = 15_000

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

export function isRecoverableChunkLoadError(reason: unknown): boolean {
  const message = typeof reason === 'string'
    ? reason
    : reason instanceof Error
      ? reason.message
      : isRecord(reason) && typeof reason.message === 'string'
        ? reason.message
        : ''

  return /Failed to fetch dynamically imported module|Importing a module script failed|error loading dynamically imported module/i.test(message)
}

function shouldReloadForChunkError(storage: Storage, now: number): boolean {
  const lastReloadRaw = storage.getItem(CHUNK_RELOAD_MARKER)
  const lastReloadAt = Number(lastReloadRaw ?? 0)
  if (Number.isFinite(lastReloadAt) && lastReloadAt > 0 && now - lastReloadAt < CHUNK_RELOAD_WINDOW_MS) {
    return false
  }
  storage.setItem(CHUNK_RELOAD_MARKER, String(now))
  return true
}

export function installChunkRecovery(targetWindow: Window = window) {
  const reloadOnce = () => {
    try {
      if (!shouldReloadForChunkError(targetWindow.sessionStorage, Date.now())) return
    } catch {
      // Ignore storage access failures and still try a single hard reload.
    }
    targetWindow.location.reload()
  }

  targetWindow.addEventListener('vite:preloadError', event => {
    event.preventDefault()
    reloadOnce()
  })

  targetWindow.addEventListener('unhandledrejection', event => {
    if (!isRecoverableChunkLoadError(event.reason)) return
    event.preventDefault()
    reloadOnce()
  })
}
