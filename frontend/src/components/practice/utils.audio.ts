import {
  __resetManagedAudioStateForTests,
  playManagedAudioUrl,
  prepareManagedAudioBuffer,
  playManagedAudioBuffer,
  stopManagedAudio,
  warmupManagedAudio,
} from './utils.audio.playback'
import { SLOW_WORD_PLAYBACK_SPEED } from './wordPlayback'

let audioGeneration = 0
let audioStopped = false

const AUDIO_BYTES_HEADER = 'x-audio-bytes'
const AUDIO_CACHE_KEY_HEADER = 'x-audio-cache-key'
const CACHE_METADATA_TTL_MS = 5_000
const MAX_WORD_AUDIO_CACHE_ENTRIES = 12

type AudioCacheEntry = { buffer: ArrayBuffer; byteLength: number; cacheKey: string | null; validatedAt: number }
type AudioMetadata = { byteLength: number | null; cacheKey: string | null }

const wordAudioCache = new Map<string, AudioCacheEntry>()
const wordAudioRequestCache = new Map<string, Promise<AudioCacheEntry | null>>()
const exampleAudioCache = new Map<string, AudioCacheEntry>()
const exampleAudioRequestCache = new Map<string, Promise<AudioCacheEntry | null>>()

function wordAudioCacheKey(word: string): string { return word.trim().toLowerCase() }
function exampleAudioCacheKey(sentence: string): string { return sentence.trim() }

function isCacheEntryIntact(entry: AudioCacheEntry | undefined): entry is AudioCacheEntry {
  return !!entry && entry.byteLength > 0 && entry.byteLength === entry.buffer.byteLength
}

function getCachedEntry(cache: Map<string, AudioCacheEntry>, key: string): AudioCacheEntry | null {
  const entry = cache.get(key)
  if (!isCacheEntryIntact(entry)) {
    cache.delete(key)
    return null
  }
  return entry
}

function rememberEntry(
  cache: Map<string, AudioCacheEntry>,
  key: string,
  entry: AudioCacheEntry,
  options?: { maxEntries?: number },
): AudioCacheEntry {
  const saved = { ...entry, validatedAt: Date.now() }
  cache.delete(key)
  cache.set(key, saved)
  const maxEntries = options?.maxEntries ?? Number.POSITIVE_INFINITY
  while (cache.size > maxEntries) {
    const oldestKey = cache.keys().next().value
    if (!oldestKey) break
    cache.delete(oldestKey)
  }
  return saved
}

function readExpectedAudioBytes(headers: Headers): number | null {
  const raw = headers.get(AUDIO_BYTES_HEADER) ?? headers.get('content-length')
  if (!raw) return null
  const parsed = Number.parseInt(raw, 10)
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null
}

function readAudioCacheKey(headers: Headers): string | null { const raw = headers.get(AUDIO_CACHE_KEY_HEADER); return raw && raw.trim() ? raw.trim() : null }
function readAudioMetadata(headers: Headers): AudioMetadata { return { byteLength: readExpectedAudioBytes(headers), cacheKey: readAudioCacheKey(headers) } }

async function decodeValidatedAudioResponse(response: Response): Promise<AudioCacheEntry | null> {
  if (!response.ok) return null
  const metadata = readAudioMetadata(response.headers)
  const expectedBytes = metadata.byteLength
  const buffer = await response.arrayBuffer()
  if (buffer.byteLength <= 0) return null
  if (expectedBytes !== null && buffer.byteLength !== expectedBytes) return null
  return {
    buffer,
    byteLength: buffer.byteLength,
    cacheKey: metadata.cacheKey,
    validatedAt: Date.now(),
  }
}

async function fetchValidatedAudioEntry(requestAudio: () => Promise<Response>): Promise<AudioCacheEntry | null> {
  for (let attempt = 0; attempt < 2; attempt += 1) {
    try {
      const response = await requestAudio()
      const entry = await decodeValidatedAudioResponse(response)
      if (entry) return entry
    } catch {
      // Retry once on transient fetch or decode failures.
    }
  }
  return null
}

async function fetchWordAudioMetadata(word: string): Promise<AudioMetadata> {
  try {
    const response = await fetch(`/api/tts/word-audio?w=${encodeURIComponent(word.trim())}&cache_only=1`, {
      method: 'HEAD',
      cache: 'no-store',
      headers: { 'Cache-Control': 'no-cache' },
    })
    return response.ok ? readAudioMetadata(response.headers) : { byteLength: null, cacheKey: null }
  } catch {
    return { byteLength: null, cacheKey: null }
  }
}

async function fetchExampleAudioMetadata(sentence: string, word: string): Promise<AudioMetadata> {
  try {
    const response = await fetch('/api/tts/example-audio', {
      method: 'POST',
      cache: 'no-store',
      headers: {
        'Cache-Control': 'no-cache',
        'Content-Type': 'application/json',
        'X-Audio-Metadata-Only': '1',
      },
      body: JSON.stringify({ sentence, word }),
    })
    return response.ok ? readAudioMetadata(response.headers) : { byteLength: null, cacheKey: null }
  } catch {
    return { byteLength: null, cacheKey: null }
  }
}

function isMetadataMatch(entry: AudioCacheEntry, metadata: AudioMetadata): boolean {
  if (metadata.byteLength === null || metadata.byteLength !== entry.byteLength) return false
  if (!metadata.cacheKey) return true
  return entry.cacheKey === metadata.cacheKey
}

async function validateCachedEntry(
  entry: AudioCacheEntry,
  requestMetadata: () => Promise<AudioMetadata>,
  options?: { force?: boolean },
): Promise<boolean> {
  if (!options?.force && Date.now() - entry.validatedAt <= CACHE_METADATA_TTL_MS) return true
  const metadata = await requestMetadata()
  if (!isMetadataMatch(entry, metadata)) return false
  if (metadata.cacheKey) entry.cacheKey = metadata.cacheKey
  entry.validatedAt = Date.now()
  return true
}

async function requestExampleAudioEntry(sentence: string, word: string): Promise<AudioCacheEntry | null> {
  return fetchValidatedAudioEntry(async () =>
    fetch('/api/tts/example-audio', {
      method: 'POST',
      cache: 'no-store',
      headers: {
        'Cache-Control': 'no-cache',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ sentence, word }),
    }),
  )
}

async function requestWordAudioEntry(word: string, cacheKey: string | null): Promise<AudioCacheEntry | null> {
  return fetchValidatedAudioEntry(async () =>
    fetch(buildWordAudioUrl(word, cacheKey), {
      method: 'GET',
      cache: 'no-store',
      headers: { 'Cache-Control': 'no-cache' },
    }),
  )
}

function buildWordAudioUrl(word: string, cacheKey: string | null): string {
  const params = new URLSearchParams({ w: word.trim() })
  params.set('cache_only', '1')
  if (cacheKey) params.set('v', cacheKey)
  return `/api/tts/word-audio?${params.toString()}`
}

function buildSegmentedWordAudioUrl(word: string, phonetic?: string | null): string {
  const params = new URLSearchParams({ w: word.trim(), pronunciation_mode: 'phonetic_segments' })
  const normalizedPhonetic = phonetic?.trim()
  if (normalizedPhonetic && normalizedPhonetic !== '/暂无音标/') {
    params.set('phonetic', normalizedPhonetic)
  }
  return `/api/tts/word-audio?${params.toString()}`
}

function buildExampleAudioUrl(sentence: string, word: string, cacheKey: string | null): string {
  const params = new URLSearchParams({ sentence: sentence.trim() })
  const trimmedWord = word.trim()
  if (trimmedWord) params.set('word', trimmedWord)
  if (cacheKey) params.set('v', cacheKey)
  return `/api/tts/example-audio?${params.toString()}`
}

async function ensureExampleAudioEntryForPlayback(
  sentence: string,
  word: string,
  options?: { forceMetadataCheck?: boolean },
): Promise<AudioCacheEntry | null> {
  const key = exampleAudioCacheKey(sentence)
  if (!key) return null
  const cached = getCachedEntry(exampleAudioCache, key)
  if (cached) {
    const isValid = await validateCachedEntry(
      cached,
      () => fetchExampleAudioMetadata(sentence, word),
      { force: options?.forceMetadataCheck ?? false },
    )
    if (isValid) return cached
    exampleAudioCache.delete(key)
  }

  const existingRequest = exampleAudioRequestCache.get(key)
  if (existingRequest) return existingRequest

  const nextRequest = requestExampleAudioEntry(sentence, word)
    .then(entry => (entry ? rememberEntry(exampleAudioCache, key, entry) : null))
    .finally(() => {
      if (exampleAudioRequestCache.get(key) === nextRequest) {
        exampleAudioRequestCache.delete(key)
      }
    })
  exampleAudioRequestCache.set(key, nextRequest)
  return nextRequest
}

async function ensureWordAudioEntryForPlayback(
  word: string,
  options?: { forceMetadataCheck?: boolean },
): Promise<AudioCacheEntry | null> {
  const key = wordAudioCacheKey(word)
  if (!key) return null
  const cached = getCachedEntry(wordAudioCache, key)
  if (cached) {
    const isValid = await validateCachedEntry(
      cached,
      () => fetchWordAudioMetadata(word),
      { force: options?.forceMetadataCheck ?? false },
    )
    if (isValid) return cached
    wordAudioCache.delete(key)
  }

  const metadata = await fetchWordAudioMetadata(word)
  if (metadata.byteLength === null && !metadata.cacheKey) return null
  const requestKey = `${key}|${metadata.cacheKey ?? ''}`
  const existingRequest = wordAudioRequestCache.get(requestKey)
  if (existingRequest) return existingRequest

  const nextRequest = requestWordAudioEntry(word, metadata.cacheKey)
    .then(entry => (entry ? rememberEntry(wordAudioCache, key, entry, { maxEntries: MAX_WORD_AUDIO_CACHE_ENTRIES }) : null))
    .finally(() => {
      if (wordAudioRequestCache.get(requestKey) === nextRequest) {
        wordAudioRequestCache.delete(requestKey)
      }
    })
  wordAudioRequestCache.set(requestKey, nextRequest)
  return nextRequest
}

export function playWord(word: string, settings: { playbackSpeed?: string; volume?: string }): void {
  void playWordAudio(word, settings)
}

export async function preloadWordAudio(word: string): Promise<boolean> {
  const entry = await ensureWordAudioEntryForPlayback(word)
  if (!entry) return false
  const [prepared] = await Promise.all([
    prepareManagedAudioBuffer(entry.buffer),
    warmupManagedAudio(),
  ])
  return prepared
}

export async function preloadExampleAudio(sentence: string, word: string): Promise<boolean> {
  const entry = await ensureExampleAudioEntryForPlayback(sentence, word)
  if (!entry) return false
  const [prepared] = await Promise.all([
    prepareManagedAudioBuffer(entry.buffer),
    warmupManagedAudio(),
  ])
  return prepared
}

export async function preloadWordAudioBatch(words: string[], lookahead = words.length): Promise<void> {
  const uniqueWords = Array.from(new Set(
    words
      .map(word => word.trim())
      .filter(Boolean),
  )).slice(0, Math.max(0, lookahead))
  await Promise.allSettled(uniqueWords.map(word => preloadWordAudio(word)))
}

export async function prepareWordAudioPlayback(word: string): Promise<boolean> {
  const trimmed = word.trim()
  if (!trimmed) return false
  const entry = await ensureWordAudioEntryForPlayback(trimmed)
  if (!entry) return false
  const [prepared] = await Promise.all([
    prepareManagedAudioBuffer(entry.buffer),
    warmupManagedAudio(),
  ])
  return prepared
}

export function playWordAudio(
  word: string,
  settings: { playbackSpeed?: string; volume?: string },
  onEnd?: () => void,
): Promise<boolean> {
  stopAudio()
  audioStopped = false
  const generation = audioGeneration
  const trimmed = word.trim()
  if (!trimmed) {
    onEnd?.()
    return Promise.resolve(false)
  }

  const volume = parseFloat(settings.volume || '100') / 100
  const rate = Math.min(4, Math.max(0.25, parseFloat(settings.playbackSpeed || '1.0')))

  return (async () => {
    try {
      const entry = await ensureWordAudioEntryForPlayback(trimmed)
      if (audioGeneration !== generation) {
        return false
      }
      if (!entry) {
        onEnd?.()
        return false
      }
      await Promise.all([
        prepareManagedAudioBuffer(entry.buffer),
        warmupManagedAudio(),
      ])
      if (audioGeneration !== generation) {
        return false
      }
      return playManagedAudioBuffer(entry.buffer, {
        isCurrent: () => audioGeneration === generation,
        isStopped: () => audioStopped,
        volume,
        rate,
        onEnd,
      })
    } catch {
      if (audioGeneration === generation) onEnd?.()
      return false
    }
  })()
}

export function playSegmentedWordAudio(
  word: string,
  settings: { playbackSpeed?: string; volume?: string },
  phonetic?: string | null,
  onEnd?: () => void,
  options?: { notifyOnFailure?: boolean },
): Promise<boolean> {
  stopAudio()
  audioStopped = false
  const generation = audioGeneration
  const trimmed = word.trim()
  if (!trimmed) {
    onEnd?.()
    return Promise.resolve(false)
  }

  return playManagedAudioUrl(buildSegmentedWordAudioUrl(trimmed, phonetic), {
    isCurrent: () => audioGeneration === generation,
    isStopped: () => audioStopped,
    volume: parseFloat(settings.volume || '100') / 100,
    rate: Math.min(4, Math.max(0.25, parseFloat(settings.playbackSpeed || '1.0'))),
    onEnd,
    notifyOnFailure: options?.notifyOnFailure ?? true,
  }).catch(() => {
    if ((options?.notifyOnFailure ?? true) && audioGeneration === generation) onEnd?.()
    return false
  })
}

export async function playSlowWordAudio(
  word: string,
  settings: { playbackSpeed?: string; volume?: string },
  phonetic?: string | null,
  onEnd?: () => void,
): Promise<boolean> {
  const startedSegmented = await playSegmentedWordAudio(
    word,
    settings,
    phonetic,
    onEnd,
    { notifyOnFailure: false },
  )
  if (startedSegmented) return true
  return playWordAudio(word, {
    ...settings,
    playbackSpeed: SLOW_WORD_PLAYBACK_SPEED,
  }, onEnd)
}

export function stopAudio(): void {
  audioStopped = true
  audioGeneration += 1
  stopManagedAudio()
}

export function __resetAudioStateForTests(): void {
  wordAudioCache.clear()
  wordAudioRequestCache.clear()
  exampleAudioCache.clear()
  exampleAudioRequestCache.clear()
  audioGeneration = 0
  audioStopped = false
  __resetManagedAudioStateForTests()
}

export function playExampleAudio(
  sentence: string,
  word: string,
  settings: { playbackSpeed?: string; volume?: string },
  onEnd?: () => void,
): void {
  stopAudio()
  audioStopped = false
  const generation = audioGeneration
  const volume = parseFloat(settings.volume || '100') / 100
  const rate = parseFloat(settings.playbackSpeed || '1')

  void (async () => {
    try {
      const [entry] = await Promise.all([
        ensureExampleAudioEntryForPlayback(sentence, word, { forceMetadataCheck: true }),
        warmupManagedAudio(),
      ])
      if (audioGeneration !== generation) {
        return
      }
      if (entry) {
        const startedFromEntry = await playManagedAudioBuffer(entry.buffer, {
          isCurrent: () => audioGeneration === generation,
          isStopped: () => audioStopped,
          volume,
          rate,
          onEnd,
        })
        if (startedFromEntry || audioGeneration !== generation) return
      }
      const playbackUrl = buildExampleAudioUrl(sentence, word, entry?.cacheKey ?? null)
      if (audioGeneration !== generation) {
        return
      }
      void playManagedAudioUrl(playbackUrl, {
        isCurrent: () => audioGeneration === generation,
        isStopped: () => audioStopped,
        volume,
        rate,
        onEnd,
      })
    } catch {
      if (audioGeneration === generation) onEnd?.()
    }
  })()
}
