import { SLOW_WORD_PLAYBACK_SPEED } from './wordPlayback'
import {
  __resetPracticeAudioSessionForTests,
  playPracticeAudio,
  stopPracticeAudio,
} from './practiceAudio.session'
import type {
  PracticeAudioRequestContext,
  WordAudioSourcePreference,
} from './practiceAudio.types'
export { preloadWordAudio, preloadWordAudioBatch, prepareWordAudioPlayback } from './utils.audio.word'

type AudioSettings = {
  playbackSpeed?: string
  volume?: string
}

type WordAudioPlayOptions = {
  sourcePreference?: WordAudioSourcePreference
}

const DEFAULT_WORD_AUDIO_PLAYBACK_OPTIONS: Required<WordAudioPlayOptions> = { sourcePreference: 'buffer' }

export function playWord(word: string, settings: AudioSettings): void {
  void playWordAudio(word, settings)
}

export function playWordAudio(
  word: string,
  settings: AudioSettings,
  onEnd?: () => void,
  options?: WordAudioPlayOptions,
  context?: PracticeAudioRequestContext,
): Promise<boolean> {
  const trimmed = word.trim()
  if (!trimmed) {
    onEnd?.()
    return Promise.resolve(false)
  }
  return playPracticeAudio({
    kind: 'word',
    word: trimmed,
    sourcePreference: options?.sourcePreference ?? DEFAULT_WORD_AUDIO_PLAYBACK_OPTIONS.sourcePreference,
  }, settings, {
    origin: context?.origin ?? 'practice-audio',
    requestId: context?.requestId,
    wordKey: context?.wordKey ?? trimmed.toLowerCase(),
    queueIndex: context?.queueIndex ?? null,
    autoplay: context?.autoplay ?? false,
  }, { onEnd })
}

export async function playSlowWordAudio(
  word: string,
  settings: AudioSettings,
  _phonetic?: string | null,
  onEnd?: () => void,
  context?: PracticeAudioRequestContext,
): Promise<boolean> {
  return playWordAudio(word, {
    ...settings,
    playbackSpeed: SLOW_WORD_PLAYBACK_SPEED,
  }, onEnd, undefined, context)
}

export function stopAudio(): void {
  stopPracticeAudio()
}

export function __resetAudioStateForTests(): void {
  __resetPracticeAudioSessionForTests()
}

export function playExampleAudio(
  sentence: string,
  word: string,
  settings: AudioSettings,
  onEnd?: () => void,
  context?: PracticeAudioRequestContext,
): void {
  const trimmedSentence = sentence.trim()
  if (!trimmedSentence) {
    onEnd?.()
    return
  }
  void playPracticeAudio({
    kind: 'example',
    sentence: trimmedSentence,
    word,
  }, settings, {
    origin: context?.origin ?? 'practice-example-audio',
    requestId: context?.requestId,
    wordKey: context?.wordKey ?? word.trim().toLowerCase(),
    queueIndex: context?.queueIndex ?? null,
    autoplay: context?.autoplay ?? false,
  }, {
    forceMetadataCheck: true,
    onEnd,
  })
}
