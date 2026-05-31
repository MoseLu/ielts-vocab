import {
  playManagedAudioBuffer,
  playManagedAudioUrl,
  prepareManagedAudioBuffer,
  prepareManagedAudioUrl,
  warmupManagedAudio,
} from './utils.audio.playback'
import {
  __resetPracticeAudioResourceStateForTests,
  buildWordAudioMetadataUrl,
  buildWordAudioUrl,
  invalidateWordAudioUrlCache,
  resolveWordAudioAsset,
} from './practiceAudio.resources'
import {
  preparePracticeAudio,
  preloadPracticeAudio,
} from './practiceAudio.session'
import type { WordAudioSourcePreference } from './practiceAudio.types'

export type WordAudioPlaybackSource =
  | { kind: 'url'; cacheKey: string; signedUrl: string }
  | { kind: 'buffer'; buffer: ArrayBuffer }

export type WordAudioPlaybackOptions = Parameters<typeof playManagedAudioUrl>[1]

type PrepareWordAudioOptions = {
  includeBuffer?: boolean
  sourcePreference?: WordAudioSourcePreference
}

async function resolveWordSource(
  word: string,
  sourcePreference: WordAudioSourcePreference = 'buffer',
): Promise<WordAudioPlaybackSource | null> {
  const asset = await resolveWordAudioAsset({ kind: 'word', word, sourcePreference })
  const clip = asset?.clips[0]
  if (!clip) return null
  if (clip.buffer) return { kind: 'buffer', buffer: clip.buffer }
  if (!clip.fallbackUrl) return null
  return {
    kind: 'url',
    cacheKey: asset?.cacheKey ?? word.trim().toLowerCase(),
    signedUrl: clip.fallbackUrl,
  }
}

export async function resolveWordAudioPlaybackSource(word: string): Promise<WordAudioPlaybackSource | null> {
  return resolveWordSource(word, 'url')
}

export async function resolveWordAudioBufferFallbackSource(word: string): Promise<WordAudioPlaybackSource | null> {
  return resolveWordSource(word, 'buffer')
}

export async function resolveWordAudioPlaybackSourceWithPreference(
  word: string,
  sourcePreference: WordAudioSourcePreference = 'buffer',
): Promise<WordAudioPlaybackSource | null> {
  return resolveWordSource(word, sourcePreference)
}

export async function prepareWordAudioSource(source: WordAudioPlaybackSource): Promise<boolean> {
  const [prepared] = await Promise.all([
    source.kind === 'url'
      ? prepareManagedAudioUrl(source.signedUrl)
      : prepareManagedAudioBuffer(source.buffer),
    warmupManagedAudio(),
  ])
  return prepared
}

export async function playWordAudioSource(
  source: WordAudioPlaybackSource,
  options: WordAudioPlaybackOptions,
): Promise<boolean> {
  if (source.kind === 'url') return playManagedAudioUrl(source.signedUrl, options)
  return playManagedAudioBuffer(source.buffer, options)
}

export async function preloadWordAudio(word: string, options?: PrepareWordAudioOptions): Promise<boolean> {
  const trimmed = word.trim()
  if (!trimmed) return false
  return preparePracticeAudio({
    kind: 'word',
    word: trimmed,
    sourcePreference: options?.sourcePreference ?? 'buffer',
  })
}

export async function preloadWordAudioBatch(
  words: string[],
  lookahead = words.length,
  options?: PrepareWordAudioOptions,
): Promise<void> {
  const uniqueWords = Array.from(new Set(
    words.map(word => word.trim()).filter(Boolean),
  )).slice(0, Math.max(0, lookahead))
  await preloadPracticeAudio(uniqueWords.map(word => ({
    kind: 'word' as const,
    word,
    sourcePreference: options?.sourcePreference ?? 'buffer',
  })))
}

export async function prepareWordAudioPlayback(word: string, options?: PrepareWordAudioOptions): Promise<boolean> {
  return preloadWordAudio(word, options)
}

export function __resetWordAudioStateForTests(): void {
  __resetPracticeAudioResourceStateForTests()
}

export {
  buildWordAudioMetadataUrl,
  buildWordAudioUrl,
  invalidateWordAudioUrlCache,
}
