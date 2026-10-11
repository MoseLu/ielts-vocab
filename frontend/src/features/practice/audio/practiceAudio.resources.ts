import { apiRequest, buildApiUrl } from '../../../lib'
import type { ExampleAudioRequest, FollowSequenceAudioRequest, PracticeAudioRequest, PreparedAudioAsset, PreparedAudioClip, WordAudioRequest } from './practiceAudio.types'
import {
  fetchValidatedAudioEntry,
  getCachedBinaryEntry,
  normalizeWordKey,
  readAudioMetadata,
  readNonEmptyString,
  readPositiveInteger,
  rememberBinaryEntry,
  validateCachedEntry,
  type AudioBinaryEntry,
  type AudioMetadata,
} from './practiceAudio.cache'

type WordAudioMetadata = AudioMetadata & {
  signedUrl: string | null
}

type WordAudioUrlEntry = {
  signedUrl: string
  cacheKey: string | null
  validatedAt: number
}

const MAX_WORD_AUDIO_CACHE_ENTRIES = 12
const WORD_AUDIO_CACHE_PROBE_TIMEOUT_MS = 1_500
const WORD_AUDIO_GENERATE_TIMEOUT_MS = 12_000

const wordBinaryCache = new Map<string, AudioBinaryEntry>()
const wordBinaryRequestCache = new Map<string, Promise<AudioBinaryEntry | null>>()
const wordUrlCache = new Map<string, WordAudioUrlEntry>()
const wordUrlMissCache = new Set<string>()
const wordMetadataRequestCache = new Map<string, Promise<WordAudioUrlEntry | null>>()
const exampleBinaryCache = new Map<string, AudioBinaryEntry>()
const exampleBinaryRequestCache = new Map<string, Promise<AudioBinaryEntry | null>>()
const followBinaryCache = new Map<string, AudioBinaryEntry>()
const followBinaryRequestCache = new Map<string, Promise<AudioBinaryEntry | null>>()

function buildWordAudioMetadataUrl(word: string): string {
  return buildApiUrl(`/api/tts/word-audio/metadata?${new URLSearchParams({ w: word.trim() }).toString()}`)
}

function buildWordAudioUrl(word: string, cacheKey: string | null): string {
  const params = new URLSearchParams({ w: word.trim() })
  params.set('cache_only', '1')
  if (cacheKey) params.set('v', cacheKey)
  return buildApiUrl(`/api/tts/word-audio?${params.toString()}`)
}

function buildGeneratedWordAudioUrl(word: string): string {
  return buildApiUrl(`/api/tts/word-audio?${new URLSearchParams({ w: word.trim() }).toString()}`)
}

async function fetchWordAudioCacheProbe(url: string, method: 'GET' | 'HEAD'): Promise<Response> {
  return apiRequest(url, {
    method,
    cache: 'no-store',
    headers: { 'Cache-Control': 'no-cache', 'X-Audio-Cache-Probe': '1' },
    timeoutMs: WORD_AUDIO_CACHE_PROBE_TIMEOUT_MS,
  })
}

async function fetchWordAudioMetadata(word: string): Promise<WordAudioMetadata> {
  try {
    const response = await apiRequest(buildWordAudioMetadataUrl(word), {
      method: 'GET',
      cache: 'no-store',
      headers: { 'Cache-Control': 'no-cache' },
    })
    if (!response.ok) return { byteLength: null, cacheKey: null, signedUrl: null }
    const payload = await response.json() as Record<string, unknown>
    return {
      byteLength: readPositiveInteger(payload.byte_length),
      cacheKey: readNonEmptyString(payload.cache_key),
      signedUrl: readNonEmptyString(payload.signed_url),
    }
  } catch {
    return { byteLength: null, cacheKey: null, signedUrl: null }
  }
}

function getCachedWordAudioUrlEntry(key: string): WordAudioUrlEntry | null {
  const entry = wordUrlCache.get(key)
  if (!entry?.signedUrl) {
    wordUrlCache.delete(key)
    return null
  }
  return entry
}

function rememberWordAudioUrlEntry(key: string, metadata: WordAudioMetadata): WordAudioUrlEntry | null {
  if (!metadata.signedUrl) {
    wordUrlCache.delete(key)
    wordUrlMissCache.add(key)
    return null
  }
  wordUrlMissCache.delete(key)
  const saved = {
    signedUrl: metadata.signedUrl,
    cacheKey: metadata.cacheKey,
    validatedAt: Date.now(),
  }
  wordUrlCache.delete(key)
  wordUrlCache.set(key, saved)
  while (wordUrlCache.size > MAX_WORD_AUDIO_CACHE_ENTRIES) {
    const oldestKey = wordUrlCache.keys().next().value
    if (!oldestKey) break
    wordUrlCache.delete(oldestKey)
  }
  return saved
}

async function ensureWordAudioUrlEntry(word: string): Promise<WordAudioUrlEntry | null> {
  const key = normalizeWordKey(word)
  if (!key) return null
  const cached = getCachedWordAudioUrlEntry(key)
  if (cached || wordUrlMissCache.has(key)) return cached
  const requestKey = `${key}|metadata`
  const existingRequest = wordMetadataRequestCache.get(requestKey)
  if (existingRequest) return existingRequest
  const nextRequest = fetchWordAudioMetadata(word)
    .then(metadata => rememberWordAudioUrlEntry(key, metadata))
    .finally(() => {
      if (wordMetadataRequestCache.get(requestKey) === nextRequest) {
        wordMetadataRequestCache.delete(requestKey)
      }
    })
  wordMetadataRequestCache.set(requestKey, nextRequest)
  return nextRequest
}

async function requestWordAudioEntry(word: string, cacheKey: string | null): Promise<AudioBinaryEntry | null> {
  return fetchValidatedAudioEntry(() => fetchWordAudioCacheProbe(buildWordAudioUrl(word, cacheKey), 'GET'))
}

async function requestGeneratedWordAudioEntry(word: string): Promise<AudioBinaryEntry | null> {
  return fetchValidatedAudioEntry(() => apiRequest(buildGeneratedWordAudioUrl(word), {
    method: 'GET',
    cache: 'no-store',
    headers: { 'Cache-Control': 'no-cache' },
    timeoutMs: WORD_AUDIO_GENERATE_TIMEOUT_MS,
  }))
}

async function ensureWordAudioEntry(word: string): Promise<AudioBinaryEntry | null> {
  const key = normalizeWordKey(word)
  if (!key) return null
  const cached = getCachedBinaryEntry(wordBinaryCache, key)
  if (cached) return cached
  const requestKey = `${key}|cache-only`
  const existingRequest = wordBinaryRequestCache.get(requestKey)
  if (existingRequest) return existingRequest
  const nextRequest = requestWordAudioEntry(word, null)
    .then(entry => (entry ? rememberBinaryEntry(wordBinaryCache, key, entry, MAX_WORD_AUDIO_CACHE_ENTRIES) : null))
    .finally(() => {
      if (wordBinaryRequestCache.get(requestKey) === nextRequest) {
        wordBinaryRequestCache.delete(requestKey)
      }
    })
  wordBinaryRequestCache.set(requestKey, nextRequest)
  return nextRequest
}

async function ensureGeneratedWordAudioEntry(word: string): Promise<AudioBinaryEntry | null> {
  const key = normalizeWordKey(word)
  if (!key) return null
  const cached = await ensureWordAudioEntry(word)
  if (cached) return cached
  const requestKey = `${key}|generated`
  const existingRequest = wordBinaryRequestCache.get(requestKey)
  if (existingRequest) return existingRequest
  const nextRequest = requestGeneratedWordAudioEntry(word)
    .then(entry => (entry ? rememberBinaryEntry(wordBinaryCache, key, entry, MAX_WORD_AUDIO_CACHE_ENTRIES) : null))
    .finally(() => {
      if (wordBinaryRequestCache.get(requestKey) === nextRequest) {
        wordBinaryRequestCache.delete(requestKey)
      }
    })
  wordBinaryRequestCache.set(requestKey, nextRequest)
  return nextRequest
}

function buildExampleAudioUrl(sentence: string, word: string, cacheKey: string | null): string {
  const params = new URLSearchParams({ sentence: sentence.trim() })
  const trimmedWord = word.trim()
  if (trimmedWord) params.set('word', trimmedWord)
  if (cacheKey) params.set('v', cacheKey)
  return buildApiUrl(`/api/tts/example-audio?${params.toString()}`)
}

async function fetchExampleAudioMetadata(sentence: string, word: string): Promise<AudioMetadata> {
  try {
    const response = await apiRequest('/api/tts/example-audio', {
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

async function ensureExampleAudioEntry(
  sentence: string,
  word: string,
  forceMetadataCheck = false,
): Promise<AudioBinaryEntry | null> {
  const key = sentence.trim()
  if (!key) return null
  const cached = getCachedBinaryEntry(exampleBinaryCache, key)
  if (cached) {
    const isValid = await validateCachedEntry(cached, () => fetchExampleAudioMetadata(sentence, word), forceMetadataCheck)
    if (isValid) return cached
    exampleBinaryCache.delete(key)
  }
  const existingRequest = exampleBinaryRequestCache.get(key)
  if (existingRequest) return existingRequest
  const nextRequest = fetchValidatedAudioEntry(async () =>
    apiRequest('/api/tts/example-audio', {
      method: 'POST',
      cache: 'no-store',
      headers: {
        'Cache-Control': 'no-cache',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ sentence, word }),
    }))
    .then(entry => (entry ? rememberBinaryEntry(exampleBinaryCache, key, entry) : null))
    .finally(() => {
      if (exampleBinaryRequestCache.get(key) === nextRequest) {
        exampleBinaryRequestCache.delete(key)
      }
    })
  exampleBinaryRequestCache.set(key, nextRequest)
  return nextRequest
}

async function ensureFollowClipEntry(
  cacheKey: string,
  clipUrl: string,
): Promise<AudioBinaryEntry | null> {
  const cached = getCachedBinaryEntry(followBinaryCache, cacheKey)
  if (cached) return cached
  const existingRequest = followBinaryRequestCache.get(cacheKey)
  if (existingRequest) return existingRequest
  const nextRequest = fetchValidatedAudioEntry(async () =>
    apiRequest(clipUrl, {
      method: 'GET',
      cache: 'no-store',
      headers: { 'Cache-Control': 'no-cache' },
    }))
    .then(entry => (entry ? rememberBinaryEntry(followBinaryCache, cacheKey, entry) : null))
    .finally(() => {
      if (followBinaryRequestCache.get(cacheKey) === nextRequest) {
        followBinaryRequestCache.delete(cacheKey)
      }
    })
  followBinaryRequestCache.set(cacheKey, nextRequest)
  return nextRequest
}

function createAssetClip(clip: PreparedAudioClip): PreparedAudioClip {
  return {
    clipId: clip.clipId,
    buffer: clip.buffer,
    fallbackUrl: clip.fallbackUrl,
    cacheKey: clip.cacheKey,
    durationMs: clip.durationMs,
    playbackRate: clip.playbackRate,
    trackTimeline: clip.trackTimeline,
  }
}

export async function resolveWordAudioAsset(request: WordAudioRequest): Promise<PreparedAudioAsset | null> {
  const wordKey = normalizeWordKey(request.word)
  if (!wordKey) return null
  const sourcePreference = request.sourcePreference ?? 'buffer'
  if (sourcePreference === 'url') {
    const urlEntry = await ensureWordAudioUrlEntry(request.word)
    if (urlEntry) {
      return {
        assetId: `word:${wordKey}:url`,
        kind: 'word',
        wordKey,
        cacheKey: urlEntry.cacheKey,
        clips: [createAssetClip({
          clipId: `word:${wordKey}`,
          buffer: null,
          fallbackUrl: urlEntry.signedUrl,
          cacheKey: urlEntry.cacheKey,
          durationMs: null,
          playbackRate: 1,
          trackTimeline: false,
        })],
        request,
      }
    }
  }
  const entry = sourcePreference === 'generated'
    ? await ensureGeneratedWordAudioEntry(request.word)
    : await ensureWordAudioEntry(request.word)
  if (!entry) return null
  const fallbackUrl = entry.cacheKey
    ? buildWordAudioUrl(request.word, entry.cacheKey)
    : buildGeneratedWordAudioUrl(request.word)
  return {
    assetId: `word:${wordKey}:${sourcePreference === 'generated' ? 'generated' : 'buffer'}`,
    kind: 'word',
    wordKey,
    cacheKey: entry.cacheKey,
    clips: [createAssetClip({
      clipId: `word:${wordKey}`,
      buffer: entry.buffer,
      fallbackUrl,
      cacheKey: entry.cacheKey,
      durationMs: null,
      playbackRate: 1,
      trackTimeline: false,
    })],
    request,
  }
}

export function invalidateWordAudioUrlCache(cacheKey: string): void {
  if (!cacheKey) return
  wordUrlCache.delete(cacheKey)
  wordUrlMissCache.delete(cacheKey)
}

export async function resolveExampleAudioAsset(
  request: ExampleAudioRequest,
  forceMetadataCheck = false,
): Promise<PreparedAudioAsset | null> {
  const entry = await ensureExampleAudioEntry(request.sentence, request.word, forceMetadataCheck)
  if (!entry) return null
  const wordKey = normalizeWordKey(request.word)
  return {
    assetId: `example:${request.sentence.trim()}:${wordKey}`,
    kind: 'example',
    wordKey,
    cacheKey: entry.cacheKey,
    clips: [createAssetClip({
      clipId: `example:${wordKey}`,
      buffer: entry.buffer,
      fallbackUrl: buildExampleAudioUrl(request.sentence, request.word, entry.cacheKey),
      cacheKey: entry.cacheKey,
      durationMs: null,
      playbackRate: 1,
      trackTimeline: false,
    })],
    request,
  }
}

export async function resolveFollowSequenceAudioAsset(
  request: FollowSequenceAudioRequest,
): Promise<PreparedAudioAsset | null> {
  const payload = request.payload
  const wordKey = normalizeWordKey(payload.word)
  if (!wordKey) return null
  const clips = await Promise.all((payload.audio_sequence?.length ? payload.audio_sequence : [{
    id: 'full-fallback',
    kind: 'full',
    label: '完整示范',
    url: payload.audio_url,
    playback_rate: payload.audio_playback_rate || 1,
    track_segments: true,
  }]).map(async (clip, index) => {
    const fallbackUrl = buildApiUrl(clip.url)
    const clipCacheKey = clip.cache_key?.trim() || `${wordKey}:${clip.id || index}:${fallbackUrl}`
    const entry = await ensureFollowClipEntry(clipCacheKey, fallbackUrl)
    return createAssetClip({
      clipId: clip.id || `follow-${index}`,
      buffer: entry?.buffer ?? null,
      fallbackUrl,
      cacheKey: entry?.cacheKey ?? clip.cache_key ?? clipCacheKey,
      durationMs: clip.track_segments ? payload.estimated_duration_ms : null,
      playbackRate: Math.min(1.15, Math.max(0.72, Number(clip.playback_rate) || 1)),
      trackTimeline: Boolean(clip.track_segments),
    })
  }))
  return {
    assetId: `follow:${wordKey}`,
    kind: 'follow-sequence',
    wordKey,
    cacheKey: clips[0]?.cacheKey ?? null,
    clips,
    request,
    timeline: payload.segments,
  }
}

export async function resolvePracticeAudioAsset(request: PracticeAudioRequest, options?: { forceMetadataCheck?: boolean }): Promise<PreparedAudioAsset | null> {
  if (request.kind === 'word') return resolveWordAudioAsset(request)
  if (request.kind === 'example') return resolveExampleAudioAsset(request, options?.forceMetadataCheck ?? false)
  return resolveFollowSequenceAudioAsset(request)
}

export function __resetPracticeAudioResourceStateForTests(): void {
  wordBinaryCache.clear(); wordBinaryRequestCache.clear(); wordUrlCache.clear(); wordUrlMissCache.clear()
  wordMetadataRequestCache.clear(); exampleBinaryCache.clear(); exampleBinaryRequestCache.clear()
  followBinaryCache.clear(); followBinaryRequestCache.clear()
}

export { buildExampleAudioUrl, buildWordAudioMetadataUrl, buildWordAudioUrl, normalizeWordKey }
