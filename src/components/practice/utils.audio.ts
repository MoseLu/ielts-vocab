let currentAudio: HTMLAudioElement | null = null
let audioGeneration = 0
let audioStopped = false
let htmlAudioWarmupPromise: Promise<void> | null = null

const SILENT_WAV_DATA_URI =
  'data:audio/wav;base64,UklGRlYAAABXQVZFZm10IBAAAAABAAEAIlYAAESsAAACABAAZGF0YTIAAACA'
const wordAudioCache = new Map<string, ArrayBuffer>()
const wordAudioInFlight = new Map<string, Promise<ArrayBuffer | null>>()
const exampleAudioCache = new Map<string, ArrayBuffer>()

function wordAudioCacheKey(word: string): string {
  return word.trim().toLowerCase()
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

async function fetchWordAudioBuffer(word: string): Promise<ArrayBuffer | null> {
  const key = wordAudioCacheKey(word)
  if (!key) return null
  if (wordAudioCache.has(key)) return wordAudioCache.get(key) ?? null
  if (wordAudioInFlight.has(key)) return wordAudioInFlight.get(key) ?? null

  const request = (async () => {
    try {
      const response = await fetch(`/api/tts/word-audio?w=${encodeURIComponent(word.trim())}`, {
        cache: 'no-store',
        headers: { 'Cache-Control': 'no-cache' },
      })
      if (!response.ok) return null
      const buffer = await response.arrayBuffer()
      wordAudioCache.set(key, buffer)
      return buffer
    } catch {
      return null
    } finally {
      wordAudioInFlight.delete(key)
    }
  })()

  wordAudioInFlight.set(key, request)
  return request
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
  const [buffer] = await Promise.all([fetchWordAudioBuffer(word), warmupHtmlAudio()])
  return buffer != null
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
  const cachedBuffer = wordAudioCache.get(wordAudioCacheKey(trimmed))

  if (cachedBuffer) {
    return warmupHtmlAudio()
      .then(() => (audioGeneration !== generation ? false : playAudioBuffer(generation, cachedBuffer, volume, rate, onEnd)))
      .catch(() => {
        if (audioGeneration === generation) onEnd?.()
        return false
      })
  }

  return (async () => {
    try {
      const [buffer] = await Promise.all([fetchWordAudioBuffer(trimmed), warmupHtmlAudio()])
      if (audioGeneration !== generation || !buffer) {
        if (audioGeneration === generation && !buffer) onEnd?.()
        return false
      }
      return playAudioBuffer(generation, buffer, volume, rate, onEnd)
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

  const cachedBuffer = exampleAudioCache.get(sentence)
  if (cachedBuffer) {
    void warmupHtmlAudio().then(() => {
      if (audioGeneration === generation) {
        void playAudioBuffer(generation, cachedBuffer, volume, rate, onEnd)
      }
    })
    return
  }

  const warmup = warmupHtmlAudio()
  void (async () => {
    try {
      const response = await fetch('/api/tts/example-audio', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sentence, word }),
      })
      await warmup
      if (audioGeneration !== generation) return
      if (!response.ok) {
        onEnd?.()
        return
      }
      const buffer = await response.arrayBuffer()
      exampleAudioCache.set(sentence, buffer)
      void playAudioBuffer(generation, buffer, volume, rate, onEnd)
    } catch {
      if (audioGeneration === generation) onEnd?.()
    }
  })()
}
