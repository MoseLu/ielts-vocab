import { apiRequest, buildApiUrl } from '../../lib'
import type { ExampleAudioRequest, FollowSequenceAudioRequest, PracticeAudioRequest, PreparedAudioAsset, PreparedAudioClip, WordAudioRequest } from './practiceAudio.types'

type AudioBinaryEntry = {
  buffer: ArrayBuffer
  byteLength: number
  cacheKey: string | null
  validatedAt: number
}

type AudioMetadata = {
  byteLength: number | null
  cacheKey: string | null
}

type WordAudioMetadata = AudioMetadata & {
  signedUrl: string | null
}

type WordAudioUrlEntry = {
  signedUrl: string
  cacheKey: string | null
  validatedAt: number
}

const AUDIO_BYTES_HEADER = 'x-audio-bytes'
const AUDIO_CACHE_KEY_HEADER = 'x-audio-cache-key'
const MAX_WORD_AUDIO_CACHE_ENTRIES = 12
const WORD_AUDIO_CACHE_PROBE_TIMEOUT_MS = 1_500

const wordBinaryCache = new Map<string, AudioBinaryEntry>()
const wordBinaryRequestCache = new Map<string, Promise<AudioBinaryEntry | null>>()
const wordUrlCache = new Map<string, WordAudioUrlEntry>()
const wordUrlMissCache = new Set<string>()
const wordMetadataRequestCache = new Map<string, Promise<WordAudioUrlEntry | null>>()
const exampleBinaryCache = new Map<string, AudioBinaryEntry>()
const exampleBinaryRequestCache = new Map<string, Promise<AudioBinaryEntry | null>>()
const followBinaryCache = new Map<string, AudioBinaryEntry>()
const followBinaryRequestCache = new Map<string, Promise<AudioBinaryEntry | null>>()

function normalizeWordKey(word: string | null | undefined): string {
  return (word ?? '').trim().toLowerCase()
}

function readPositiveInteger(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value) && value > 0) return Math.trunc(value)
  if (typeof value !== 'string') return null
  const parsed = Number.parseInt(value, 10)
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null
}

function readNonEmptyString(value: unknown): string | null {
  return typeof value === 'string' && value.trim() ? value.trim() : null
}

function readExpectedAudioBytes(headers: Headers): number | null {
  const raw = headers.get(AUDIO_BYTES_HEADER) ?? headers.get('content-length')
  if (!raw) return null
  const parsed = Number.parseInt(raw, 10)
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null
}

function readAudioCacheKey(headers: Headers): string | null {
  const raw = headers.get(AUDIO_CACHE_KEY_HEADER)
  return raw && raw.trim() ? raw.trim() : null
}

function readAudioMetadata(headers: Headers): AudioMetadata {
  return {
    byteLength: readExpectedAudioBytes(headers),
    cacheKey: readAudioCacheKey(headers),
  }
}

function isBinaryEntryIntact(entry: AudioBinaryEntry | undefined): entry is AudioBinaryEntry {
  return !!entry && entry.byteLength > 0 && entry.byteLength === entry.buffer.byteLength
}

function getCachedBinaryEntry(cache: Map<string, AudioBinaryEntry>, key: string): AudioBinaryEntry | null {
  const entry = cache.get(key)
  if (!isBinaryEntryIntact(entry)) {
    cache.delete(key)
    return null
  }
  return entry
}

function rememberBinaryEntry(
  cache: Map<string, AudioBinaryEntry>,
  key: string,
  entry: AudioBinaryEntry,
  maxEntries = Number.POSITIVE_INFINITY,
): AudioBinaryEntry {
  const saved = { ...entry, validatedAt: Date.now() }
  cache.delete(key)
  cache.set(key, saved)
  while (cache.size > maxEntries) {
    const oldestKey = cache.keys().next().value
    if (!oldestKey) break
    cache.delete(oldestKey)
  }
  return saved
}

async function decodeValidatedAudioResponse(response: Response): Promise<AudioBinaryEntry | null> {
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

async function fetchValidatedAudioEntry(requestAudio: () => Promise<Response>): Promise<AudioBinaryEntry | null> {
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

function isMetadataMatch(entry: AudioBinaryEntry, metadata: AudioMetadata): boolean {
  if (metadata.byteLength === null || metadata.byteLength !== entry.byteLength) return false
  if (!metadata.cacheKey) return true
  return entry.cacheKey === metadata.cacheKey
}

async function validateCachedEntry(
  entry: AudioBinaryEntry,
  requestMetadata: () => Promise<AudioMetadata>,
  force = false,
): Promise<boolean> {
  if (!force) return true
  const metadata = await requestMetadata()
  if (!isMetadataMatch(entry, metadata)) return false
  if (metadata.cacheKey) entry.cacheKey = metadata.cacheKey
  entry.validatedAt = Date.now()
  return true
}

function buildWordAudioMetadataUrl(word: string): string {
  return buildApiUrl(`/api/tts/word-audio/metadata?${new URLSearchParams({ w: word.trim() }).toString()}`)
}

function buildWordAudioUrl(word: string, cacheKey: string | null): string {
  const params = new URLSearchParams({ w: word.trim() })
  params.set('cache_only', '1')
  if (cacheKey) params.set('v', cacheKey)
  return buildApiUrl(`/api/tts/word-audio?${params.toString()}`)
}

async function fetchWordAudioCacheProbe(url: string, method: 'GET' | 'HEAD'): Promise<Response> {
  const request: RequestInit = {
    method,
    cache: 'no-store',
    headers: { 'Cache-Control': 'no-cache' },
  }
  if (typeof AbortController === 'undefined') return fetch(url, request)
  const controller = new AbortController()
  const timeoutId = globalThis.setTimeout(() => controller.abort(), WORD_AUDIO_CACHE_PROBE_TIMEOUT_MS)
  request.signal = controller.signal
  try {
    return await apiRequest(url, request)
  } finally {
    globalThis.clearTimeout(timeoutId)
  }
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
  const entry = await ensureWordAudioEntry(request.word)
  if (!entry) return null
  return {
    assetId: `word:${wordKey}:buffer`,
    kind: 'word',
    wordKey,
    cacheKey: entry.cacheKey,
    clips: [createAssetClip({
      clipId: `word:${wordKey}`,
      buffer: entry.buffer,
      fallbackUrl: buildWordAudioUrl(request.word, entry.cacheKey),
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
