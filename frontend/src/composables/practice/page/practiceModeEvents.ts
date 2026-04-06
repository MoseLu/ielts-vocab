export function requestPracticeMode(mode?: string | null): void {
  if (!mode) return

  window.dispatchEvent(new CustomEvent('practice-mode-request', {
    detail: { mode },
  }))
}
