export const PRACTICE_GLOBAL_SHORTCUT_PREVIOUS_EVENT = 'practice-global-shortcut:previous'
export const PRACTICE_GLOBAL_SHORTCUT_NEXT_EVENT = 'practice-global-shortcut:next'
export const PRACTICE_GLOBAL_SHORTCUT_REPLAY_EVENT = 'practice-global-shortcut:replay'

function dispatchPracticeGlobalShortcut(type: string): void {
  window.dispatchEvent(new Event(type))
}

export function dispatchPracticeGlobalShortcutPrevious(): void {
  dispatchPracticeGlobalShortcut(PRACTICE_GLOBAL_SHORTCUT_PREVIOUS_EVENT)
}

export function dispatchPracticeGlobalShortcutNext(): void {
  dispatchPracticeGlobalShortcut(PRACTICE_GLOBAL_SHORTCUT_NEXT_EVENT)
}

export function dispatchPracticeGlobalShortcutReplay(): void {
  dispatchPracticeGlobalShortcut(PRACTICE_GLOBAL_SHORTCUT_REPLAY_EVENT)
}
