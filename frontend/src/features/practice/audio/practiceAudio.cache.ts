export type AudioBinaryEntry = {
  buffer: ArrayBuffer
  byteLength: number
  cacheKey: string | null
  validatedAt: number
}

export type AudioMetadata = {
  byteLength: number | null
  cacheKey: string | null
}

const AUDIO_BYTES_HEADER = 'x-audio-bytes'
const AUDIO_CACHE_KEY_HEADER = 'x-audio-cache-key'

export function normalizeWordKey(word: string | null | undefined): string {
  return (word ?? '').trim().toLowerCase()
}

export function readPositiveInteger(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value) && value > 0) return Math.trunc(value)
  if (typeof value !== 'string') return null
  const parsed = Number.parseInt(value, 10)
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null
}

export function readNonEmptyString(value: unknown): string | null {
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

export function readAudioMetadata(headers: Headers): AudioMetadata {
  return {
    byteLength: readExpectedAudioBytes(headers),
    cacheKey: readAudioCacheKey(headers),
  }
}

function isBinaryEntryIntact(entry: AudioBinaryEntry | undefined): entry is AudioBinaryEntry {
  return !!entry && entry.byteLength > 0 && entry.byteLength === entry.buffer.byteLength
}

export function getCachedBinaryEntry(cache: Map<string, AudioBinaryEntry>, key: string): AudioBinaryEntry | null {
  const entry = cache.get(key)
  if (!isBinaryEntryIntact(entry)) {
    cache.delete(key)
    return null
  }
  return entry
}

export function rememberBinaryEntry(
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

export async function fetchValidatedAudioEntry(requestAudio: () => Promise<Response>): Promise<AudioBinaryEntry | null> {
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

export async function validateCachedEntry(
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
