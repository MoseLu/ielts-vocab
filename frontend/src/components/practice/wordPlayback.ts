import type { AppSettings, WordPlaybackOptions } from './types'

export const SLOW_WORD_PLAYBACK_SPEED = '0.65'
export const SLOW_WORD_PLAYBACK_OPTIONS: WordPlaybackOptions = {
  playbackSpeed: SLOW_WORD_PLAYBACK_SPEED,
}

export function resolveWordPlaybackSettings(
  settings: AppSettings,
  options?: WordPlaybackOptions,
): AppSettings {
  if (!options?.playbackSpeed) return settings
  return {
    ...settings,
    playbackSpeed: options.playbackSpeed,
  }
}
