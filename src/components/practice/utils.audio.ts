let currentAudio: HTMLAudioElement | null = null
let audioGeneration = 0
let audioStopped = false
let htmlAudioWarmupPromise: Promise<void> | null = null

const SILENT_WAV_DATA_URI =
  'data:audio/wav;base64,UklGRlYAAABXQVZFZm10IBAAAAABAAEAIlYAAESsAAACABAAZGF0YTIAAACA'
const AUDIO_BYTES_HEADER = 'x-audio-bytes'
const CACHE_METADATA_TTL_MS = 5_000

type AudioCacheEntry = {
  buffer: ArrayBuffer
  byteLength: number
  validatedAt: number
}

const wordAudioCache = new Map<string, AudioCacheEntry>()
const wordAudioInFlight = new Map<string, Promise<AudioCacheEntry | null>>()
const exampleAudioCache = new Map<string, AudioCacheEntry>()

function wordAudioCacheKey(word: string): string {
  return word.trim().toLowerCase()
}

function exampleAudioCacheKey(sentence: string): string {
  return sentence.trim()
}

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

function rememberEntry(cache: Map<string, AudioCacheEntry>, key: string, entry: AudioCacheEntry): AudioCacheEntry {
  const saved = { ...entry, validatedAt: Date.now() }
  cache.set(key, saved)
  return saved
}

function readExpectedAudioBytes(headers: Headers): number | null {
  const raw = headers.get(AUDIO_BYTES_HEADER) ?? headers.get('content-length')
  if (!raw) return null
  const parsed = Number.parseInt(raw, 10)
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null
}

async function decodeValidatedAudioResponse(response: Response): Promise<AudioCacheEntry | null> {
  if (!response.ok) return null
  const expectedBytes = readExpectedAudioBytes(response.headers)
  const buffer = await response.arrayBuffer()
  if (buffer.byteLength <= 0) return null
  if (expectedBytes !== null && buffer.byteLength !== expectedBytes) return null
  return {
    buffer,
    byteLength: buffer.byteLength,
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

async function fetchWordAudioMetadataBytes(word: string): Promise<number | null> {
  try {
    const response = await fetch(`/api/tts/word-audio?w=${encodeURIComponent(word.trim())}`, {
      method: 'HEAD',
      cache: 'no-store',
      headers: { 'Cache-Control': 'no-cache' },
    })
    return response.ok ? readExpectedAudioBytes(response.headers) : null
  } catch {
    return null
  }
}

async function fetchExampleAudioMetadataBytes(sentence: string, word: string): Promise<number | null> {
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
    return response.ok ? readExpectedAudioBytes(response.headers) : null
  } catch {
    return null
  }
}

async function validateCachedEntry(
  entry: AudioCacheEntry,
  requestMetadataBytes: () => Promise<number | null>,
): Promise<boolean> {
  if (Date.now() - entry.validatedAt <= CACHE_METADATA_TTL_MS) return true
  const expectedBytes = await requestMetadataBytes()
  if (expectedBytes === null || expectedBytes !== entry.byteLength) return false
  entry.validatedAt = Date.now()
  return true
}

async function requestWordAudioEntry(word: string): Promise<AudioCacheEntry | null> {
  return fetchValidatedAudioEntry(async () =>
    fetch(`/api/tts/word-audio?w=${encodeURIComponent(word.trim())}`, {
      cache: 'no-store',
      headers: { 'Cache-Control': 'no-cache' },
    }),
  )
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

async function fetchWordAudioBuffer(word: string): Promise<AudioCacheEntry | null> {
  const key = wordAudioCacheKey(word)
  if (!key) return null
  const cached = getCachedEntry(wordAudioCache, key)
  if (cached) return cached
  if (wordAudioInFlight.has(key)) return wordAudioInFlight.get(key) ?? null

  const request = (async () => {
    try {
      const entry = await requestWordAudioEntry(word)
      return entry ? rememberEntry(wordAudioCache, key, entry) : null
    } finally {
      wordAudioInFlight.delete(key)
    }
  })()

  wordAudioInFlight.set(key, request)
  return request
}

async function ensureWordAudioEntryForPlayback(word: string): Promise<AudioCacheEntry | null> {
  const key = wordAudioCacheKey(word)
  if (!key) return null
  const cached = getCachedEntry(wordAudioCache, key)
  if (cached) {
    const isValid = await validateCachedEntry(cached, () => fetchWordAudioMetadataBytes(word))
    if (isValid) return cached
    wordAudioCache.delete(key)
  }
  return fetchWordAudioBuffer(word)
}

async function ensureExampleAudioEntryForPlayback(sentence: string, word: string): Promise<AudioCacheEntry | null> {
  const key = exampleAudioCacheKey(sentence)
  if (!key) return null
  const cached = getCachedEntry(exampleAudioCache, key)
  if (cached) {
    const isValid = await validateCachedEntry(cached, () => fetchExampleAudioMetadataBytes(sentence, word))
    if (isValid) return cached
    exampleAudioCache.delete(key)
  }
  const entry = await requestExampleAudioEntry(sentence, word)
  return entry ? rememberEntry(exampleAudioCache, key, entry) : null
}

function warmupHtmlAudio(): Promise<void> {
  if (htmlAudioWarmupPromise) return htmlAudioWarmupPromise
  htmlAudioWarmupPromise = new Promise(resolve => {
    try {
      const audio = new Audio(SILENT_WAV_DATA_URI)
      audio.volume = 0
      let settled = false
      const finish = () => {
        if (settled) return
        settled = true
        resolve()
      }
      audio.onended = finish
      audio.onerror = finish
      setTimeout(finish, 1200)
      audio.play().catch(finish)
    } catch {
      resolve()
    }
  })
  return htmlAudioWarmupPromise
}

async function playAudioBuffer(
  generation: number,
  buffer: ArrayBuffer,
  volume: number,
  rate: number,
  onEnd?: () => void,
): Promise<boolean> {
  const blobUrl = URL.createObjectURL(new Blob([buffer], { type: 'audio/mpeg' }))
  const audio = new Audio(blobUrl)
  audio.volume = volume
  audio.playbackRate = rate
  currentAudio = audio

  let settled = false
  let started = false
  const cleanup = () => URL.revokeObjectURL(blobUrl)
  const cancel = (resolve: (value: boolean) => void) => {
    if (settled) return
    settled = true
    cleanup()
    if (currentAudio === audio) currentAudio = null
    resolve(started)
  }

  return new Promise(resolve => {
    const markStarted = () => {
      if (audioGeneration !== generation) {
        cancel(resolve)
        return
      }
      if (started || settled) return
      started = true
      resolve(true)
    }

    const fail = () => {
      if (audioGeneration !== generation) {
        cancel(resolve)
        return
      }
      if (settled) return
      settled = true
      cleanup()
      if (currentAudio === audio) currentAudio = null
      resolve(started)
      onEnd?.()
    }

    audio.onerror = fail
    audio.onended = () => {
      if (audioGeneration !== generation) {
        cancel(resolve)
        return
      }
      if (settled) return
      settled = true
      cleanup()
      if (currentAudio === audio) currentAudio = null
      resolve(started)
      if (!audioStopped) onEnd?.()
    }

    const start = () => {
      if (audioGeneration !== generation) {
        cancel(resolve)
        return
      }
      if (settled) return
      try {
        const result = audio.play()
        if (result && typeof result.then === 'function') {
          void result.then(markStarted).catch(fail)
        } else {
          markStarted()
        }
      } catch {
        fail()
      }
    }

    if (typeof audio.addEventListener === 'function') {
      audio.addEventListener('playing', markStarted, { once: true })
    }

    if (audio.readyState >= 2) {
      start()
    } else if (typeof audio.addEventListener === 'function') {
      audio.addEventListener('canplaythrough', start, { once: true })
      audio.load()
    } else {
      start()
    }
  })
}

export function playWord(word: string, settings: { playbackSpeed?: string; volume?: string }): void {
  void playWordAudio(word, settings)
}

export async function preloadWordAudio(word: string): Promise<boolean> {
  return (await fetchWordAudioBuffer(word)) != null
}

export async function prepareWordAudioPlayback(word: string): Promise<boolean> {
  const [entry] = await Promise.all([ensureWordAudioEntryForPlayback(word), warmupHtmlAudio()])
  return entry != null
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
  const rate = Math.min(4, Math.max(0.25, parseFloat(settings.playbackSpeed || '0.8')))

  return (async () => {
    try {
      const [entry] = await Promise.all([ensureWordAudioEntryForPlayback(trimmed), warmupHtmlAudio()])
      if (audioGeneration !== generation || !entry) {
        if (audioGeneration === generation && !entry) onEnd?.()
        return false
      }
      return playAudioBuffer(generation, entry.buffer, volume, rate, onEnd)
    } catch {
      if (audioGeneration === generation) onEnd?.()
      return false
    }
  })()
}

export function stopAudio(): void {
  audioStopped = true
  audioGeneration += 1
  if (!currentAudio) return
  currentAudio.onended = null
  currentAudio.onerror = null
  currentAudio.pause()
  currentAudio = null
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
        ensureExampleAudioEntryForPlayback(sentence, word),
        warmupHtmlAudio(),
      ])
      if (audioGeneration !== generation || !entry) {
        if (audioGeneration === generation && !entry) onEnd?.()
        return
      }
      void playAudioBuffer(generation, entry.buffer, volume, rate, onEnd)
    } catch {
      if (audioGeneration === generation) onEnd?.()
    }
  })()
}
