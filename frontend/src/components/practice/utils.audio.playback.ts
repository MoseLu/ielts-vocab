import { getManagedAudioFailureReason, isAutoplayBlockedError, rememberManagedAudioFailureReason, resetManagedAudioFailureReason } from './utils.audio.failure'
import { ensureManagedAudioKeepAlive, fillManagedAudioLeadIn, getManagedAudioLeadInMs as readManagedAudioLeadInMs, getManagedAudioLeadingSilenceSeconds, getManagedAudioStartDelaySeconds, stopManagedAudioKeepAlive, type ManagedAudioKeepAliveState } from './utils.audio.webAudio'
const SILENT_WAV_DATA_URI = 'data:audio/wav;base64,UklGRjQAAABXQVZFZm10IBAAAAABAAEAQB8AAIA+AAACABAAZGF0YRAAAAAAAAAAAAAAAAAAAAAAAAAA'
type PlaybackOptions = {
  isCurrent: () => boolean
  isStopped: () => boolean
  volume: number
  rate: number
  onEnd?: () => void
  cleanup?: () => void
  notifyOnFailure?: boolean
}

type ManagedAudioContextCtor = new () => AudioContext
type ManagedAudioWindow = Window & typeof globalThis & { webkitAudioContext?: ManagedAudioContextCtor }
let currentAudio: HTMLAudioElement | null = null
let currentBufferSource: AudioBufferSourceNode | null = null
let currentBufferGain: GainNode | null = null
let currentPlaybackCleanup: (() => void) | null = null
let htmlAudioWarmupPromise: Promise<void> | null = null
let managedAudioContext: AudioContext | null = null
let managedAudioResumePromise: Promise<boolean> | null = null
let managedAudioOutputPrimePromise: Promise<boolean> | null = null
const managedAudioKeepAliveState: ManagedAudioKeepAliveState = { source: null, gain: null }
let removeAudioUnlockListeners: (() => void) | null = null
let audioOutputPrimed = false
let managedAudioOutputPrimed = false
let decodedBufferCache = new WeakMap<ArrayBuffer, Promise<AudioBuffer | null>>()
const preparedAudioPool = new Map<string, HTMLAudioElement>()
const preparedAudioReadyPromises = new Map<string, Promise<boolean>>()
const MAX_PREPARED_AUDIO = 4
const AUDIO_PREPARE_TIMEOUT_MS = 1_200
const AUDIO_OUTPUT_PRIME_MS = 160
const WEB_AUDIO_OUTPUT_PRIME_MS = 140
const AUDIO_UNLOCK_EVENTS = ['pointerdown', 'keydown', 'touchstart', 'mousedown'] as const
let playbackReadyBufferCache = new WeakMap<AudioBuffer, AudioBuffer>()

function cleanupPlayback(): void {
  if (!currentPlaybackCleanup) return
  const cleanup = currentPlaybackCleanup
  currentPlaybackCleanup = null
  cleanup()
}

function rememberPreparedAudio(src: string, audio: HTMLAudioElement): HTMLAudioElement {
  preparedAudioPool.delete(src)
  preparedAudioPool.set(src, audio)
  if (preparedAudioPool.size <= MAX_PREPARED_AUDIO) return audio
  const oldestSrc = preparedAudioPool.keys().next().value
  if (oldestSrc) {
    preparedAudioPool.delete(oldestSrc)
    preparedAudioReadyPromises.delete(oldestSrc)
  }
  return audio
}
async function warmupHtmlAudio(): Promise<void> {
  await new Promise<void>(resolve => {
    try {
      const audio = new Audio(SILENT_WAV_DATA_URI)
      let settled = false
      const finish = () => {
        if (settled) return
        settled = true
        audio.pause()
        resolve()
      }
      audio.muted = true
      audio.onended = finish
      audio.onerror = finish
      setTimeout(finish, 200)
      void audio.play().then(finish).catch(finish)
    } catch {
      resolve()
    }
  })
}
function getOrCreatePreparedAudio(src: string): HTMLAudioElement {
  const existing = preparedAudioPool.get(src)
  if (existing) return rememberPreparedAudio(src, existing)
  return rememberPreparedAudio(src, new Audio(src))
}
function attachAudioSource(audio: HTMLAudioElement, src: string): void {
  audio.preload = 'auto'
  if (audio.src !== src) audio.src = src
}
async function waitForPreparedAudio(audio: HTMLAudioElement, src: string, minimumReadyState = 4): Promise<boolean> {
  if (audio.readyState >= minimumReadyState) { preparedAudioReadyPromises.delete(src); return true }
  const existing = preparedAudioReadyPromises.get(src)
  if (existing) return existing
  const pending = new Promise<boolean>(resolve => {
    let settled = false
    let timerId: ReturnType<typeof setTimeout> | null = null
    const finish = (ready: boolean) => {
      if (settled) return
      settled = true
      if (timerId) clearTimeout(timerId)
      if (typeof audio.removeEventListener === 'function') {
        audio.removeEventListener('loadeddata', handleReady)
        audio.removeEventListener('canplay', handleReady)
        audio.removeEventListener('canplaythrough', handleReady)
        audio.removeEventListener('error', handleError)
      }
      if (preparedAudioReadyPromises.get(src) === pending) preparedAudioReadyPromises.delete(src)
      resolve(ready)
    }
    const handleReady = () => {
      if (audio.readyState >= minimumReadyState) finish(true)
    }
    const handleError = () => finish(false)
    if (typeof audio.addEventListener === 'function') {
      audio.addEventListener('loadeddata', handleReady)
      audio.addEventListener('canplay', handleReady)
      audio.addEventListener('canplaythrough', handleReady)
      audio.addEventListener('error', handleError)
    }
    timerId = setTimeout(() => finish(audio.readyState >= 2), AUDIO_PREPARE_TIMEOUT_MS)
    audio.load()
  })
  preparedAudioReadyPromises.set(src, pending)
  return pending
}
async function primeAudioOutput(): Promise<void> {
  if (audioOutputPrimed) return
  await new Promise<void>(resolve => {
    try {
      const primer = new Audio(SILENT_WAV_DATA_URI)
      let settled = false
      const finish = () => {
        if (settled) return
        settled = true
        primer.pause()
        resolve()
      }
      primer.muted = true
      primer.onended = finish
      primer.onerror = finish
      setTimeout(finish, AUDIO_OUTPUT_PRIME_MS)
      void primer.play().then(finish).catch(finish)
    } catch {
      resolve()
    }
  })
  audioOutputPrimed = true
}

function getAudioContextCtor(): ManagedAudioContextCtor | null {
  if (typeof window === 'undefined') return null
  const managedWindow = window as ManagedAudioWindow
  return managedWindow.AudioContext ?? managedWindow.webkitAudioContext ?? null
}
function clearAudioUnlockListeners(): void {
  if (!removeAudioUnlockListeners) return
  const cleanup = removeAudioUnlockListeners
  removeAudioUnlockListeners = null
  cleanup()
}
function canResumeManagedAudioContext(audioContext: AudioContext): boolean {
  if (audioContext.state === 'running') return true
  const activation = (navigator as Navigator & { userActivation?: { isActive?: boolean } }).userActivation
  return Boolean(activation?.isActive)
}
function ensureAudioUnlockListeners(): void {
  if (removeAudioUnlockListeners || typeof document === 'undefined') return
  const handleUserGesture = () => {
    void resumeManagedAudioContext().then(running => {
      if (running) clearAudioUnlockListeners()
    })
  }
  for (const eventName of AUDIO_UNLOCK_EVENTS) {
    document.addEventListener(eventName, handleUserGesture, true)
  }
  removeAudioUnlockListeners = () => {
    for (const eventName of AUDIO_UNLOCK_EVENTS) {
      document.removeEventListener(eventName, handleUserGesture, true)
    }
  }
}
function getOrCreateManagedAudioContext(): AudioContext | null {
  if (managedAudioContext && managedAudioContext.state !== 'closed') return managedAudioContext
  const AudioContextCtor = getAudioContextCtor()
  if (!AudioContextCtor) return null
  try {
    managedAudioContext = new AudioContextCtor()
    decodedBufferCache = new WeakMap()
    managedAudioOutputPrimed = false
    ensureAudioUnlockListeners()
    return managedAudioContext
  } catch {
    managedAudioContext = null
    return null
  }
}

async function resumeManagedAudioContext(): Promise<boolean> {
  const audioContext = getOrCreateManagedAudioContext()
  if (!audioContext) return false
  if (audioContext.state === 'running') {
    ensureManagedAudioKeepAlive(audioContext, managedAudioKeepAliveState)
    clearAudioUnlockListeners()
    return true
  }
  if (!canResumeManagedAudioContext(audioContext)) return false
  if (managedAudioResumePromise) return managedAudioResumePromise
  managedAudioResumePromise = (async () => {
    try {
      await audioContext.resume()
      if (audioContext.state === 'running') ensureManagedAudioKeepAlive(audioContext, managedAudioKeepAliveState)
      return audioContext.state === 'running'
    } catch {
      return false
    } finally {
      managedAudioResumePromise = null
      if (audioContext.state === 'running') clearAudioUnlockListeners()
    }
  })()
  return managedAudioResumePromise
}
async function decodeManagedAudioBuffer(buffer: ArrayBuffer): Promise<AudioBuffer | null> {
  if (buffer.byteLength <= 0) return null
  const audioContext = getOrCreateManagedAudioContext()
  if (!audioContext) return null
  const existing = decodedBufferCache.get(buffer)
  if (existing) return existing
  const nextDecodedBuffer = (async () => {
    try {
      return await audioContext.decodeAudioData(buffer.slice(0))
    } catch {
      return null
    }
  })()
  decodedBufferCache.set(buffer, nextDecodedBuffer)
  const decodedBuffer = await nextDecodedBuffer
  if (!decodedBuffer) decodedBufferCache.delete(buffer)
  return decodedBuffer
}
async function primeManagedAudioContextOutput(audioContext: AudioContext): Promise<boolean> {
  if (managedAudioOutputPrimed) return true
  if (audioContext.state !== 'running') return false
  if (managedAudioOutputPrimePromise) return managedAudioOutputPrimePromise
  managedAudioOutputPrimePromise = new Promise(resolve => {
    let finished = false
    const gainNode = audioContext.createGain()
    const source = audioContext.createBufferSource()
    const finish = (primed: boolean) => {
      if (finished) return
      finished = true
      source.onended = null
      try { source.disconnect() } catch {}
      try { gainNode.disconnect() } catch {}
      if (primed) managedAudioOutputPrimed = true
      managedAudioOutputPrimePromise = null
      resolve(primed)
    }
    try {
      gainNode.gain.value = 0
      source.buffer = audioContext.createBuffer(1, Math.max(1, Math.round(audioContext.sampleRate * 0.12)), audioContext.sampleRate)
      source.connect(gainNode)
      gainNode.connect(audioContext.destination)
      source.onended = () => finish(true)
      source.start(audioContext.currentTime)
      setTimeout(() => finish(true), WEB_AUDIO_OUTPUT_PRIME_MS)
    } catch {
      finish(false)
    }
  })
  return managedAudioOutputPrimePromise
}
function getPlaybackReadyBuffer(audioContext: AudioContext, buffer: AudioBuffer): AudioBuffer {
  const cached = playbackReadyBufferCache.get(buffer)
  if (cached) return cached
  const leadingFrames = Math.max(0, Math.round(buffer.sampleRate * getManagedAudioLeadingSilenceSeconds(audioContext)))
  if (leadingFrames <= 0) return buffer
  const playbackBuffer = audioContext.createBuffer(
    buffer.numberOfChannels,
    Math.max(1, buffer.length + leadingFrames),
    buffer.sampleRate,
  )
  for (let channelIndex = 0; channelIndex < buffer.numberOfChannels; channelIndex += 1) {
    const channelData = playbackBuffer.getChannelData(channelIndex)
    fillManagedAudioLeadIn(channelData, leadingFrames, channelIndex)
    channelData.set(buffer.getChannelData(channelIndex), leadingFrames)
  }
  playbackReadyBufferCache.set(buffer, playbackBuffer)
  return playbackBuffer
}
async function playWebAudioBuffer(buffer: AudioBuffer, options: PlaybackOptions): Promise<boolean> {
  const audioContext = getOrCreateManagedAudioContext()
  if (!audioContext) return false
  const canResume = canResumeManagedAudioContext(audioContext)
  const resumed = canResume ? await resumeManagedAudioContext() : false
  if (!resumed) rememberManagedAudioFailureReason('not-allowed')
  if (!resumed || !options.isCurrent()) return false
  await primeManagedAudioContextOutput(audioContext)
  if (!options.isCurrent()) return false
  const playbackBuffer = getPlaybackReadyBuffer(audioContext, buffer)
  const startDelaySeconds = getManagedAudioStartDelaySeconds(audioContext)
  const gainNode = audioContext.createGain()
  const source = audioContext.createBufferSource()
  gainNode.gain.value = options.volume
  source.buffer = playbackBuffer
  source.playbackRate.value = options.rate
  source.connect(gainNode)
  gainNode.connect(audioContext.destination)
  currentBufferSource = source
  currentBufferGain = gainNode
  currentPlaybackCleanup = options.cleanup ?? null
  let settled = false
  let started = false
  const clearCurrent = () => {
    if (currentBufferSource === source) currentBufferSource = null
    if (currentBufferGain === gainNode) currentBufferGain = null
    try { source.disconnect() } catch {}
    try { gainNode.disconnect() } catch {}
    cleanupPlayback()
  }
  const finalize = (notifyEnd: boolean) => {
    if (settled) return false
    settled = true
    source.onended = null
    clearCurrent()
    if (!started) return false
    if (notifyEnd) options.onEnd?.()
    return true
  }
  source.onended = () => {
    finalize(options.isCurrent() && !options.isStopped())
  }
  try {
    source.start(audioContext.currentTime + startDelaySeconds)
    started = true
    return true
  } catch {
    const resolved = finalize(options.notifyOnFailure !== false)
    return resolved
  }
}

async function playHtmlAudio(src: string, options: PlaybackOptions): Promise<boolean> {
  const audio = getOrCreatePreparedAudio(src)
  attachAudioSource(audio, src)
  const prepared = await waitForPreparedAudio(audio, src)
  if (!prepared || !options.isCurrent()) return false
  await primeAudioOutput()
  if (!options.isCurrent()) return false
  const needsReset = !audio.paused || audio.currentTime !== 0 || audio.ended
  if (needsReset) {
    try {
      audio.pause()
      audio.currentTime = 0
    } catch {}
    await new Promise<void>(resolve => {
      let seekSettled = false
      const onSeeked = () => {
        if (seekSettled) return
        seekSettled = true
        resolve()
      }
      if (typeof audio.addEventListener === 'function') {
        audio.addEventListener('seeked', onSeeked, { once: true })
      }
      setTimeout(onSeeked, 200)
    })
    if (!options.isCurrent()) return false
  }
  audio.volume = options.volume
  audio.playbackRate = options.rate
  currentAudio = audio
  currentPlaybackCleanup = options.cleanup ?? null
  let settled = false
  let started = false
  const clearCurrent = () => {
    if (currentAudio === audio) {
      currentAudio = null
      cleanupPlayback()
    }
  }
    const resolveIfCurrent = (resolve: (value: boolean) => void) => {
      if (settled) return
      settled = true
      clearCurrent()
      resolve(started)
    }
  return new Promise(resolve => {
    const markStarted = () => {
      if (!options.isCurrent()) return resolveIfCurrent(resolve)
      if (started || settled) return
      started = true
      resolve(true)
    }
    const fail = (reason: ManagedAudioFailureReason = 'unknown') => {
      if (!options.isCurrent()) return resolveIfCurrent(resolve)
      if (settled) return
      settled = true
      rememberManagedAudioFailureReason(reason)
      clearCurrent()
      resolve(started)
      if (options.notifyOnFailure !== false) options.onEnd?.()
    }
    audio.onerror = fail
    audio.onended = () => {
      if (!options.isCurrent()) return resolveIfCurrent(resolve)
      if (settled) return
      settled = true
      clearCurrent()
      resolve(started)
      if (!options.isStopped()) options.onEnd?.()
    }
    const start = () => {
      if (!options.isCurrent()) return resolveIfCurrent(resolve)
      if (settled) return
      try {
        const result = audio.play()
        if (result && typeof result.then === 'function') {
          void result.then(markStarted).catch(error => {
            fail(isAutoplayBlockedError(error) ? 'not-allowed' : 'unknown')
          })
        }
        else markStarted()
      } catch {
        fail()
      }
    }
    if (typeof audio.addEventListener === 'function') audio.addEventListener('playing', markStarted, { once: true })
    if (audio.readyState >= 4) start()
    else if (typeof audio.addEventListener === 'function') {
      audio.addEventListener('canplaythrough', start, { once: true })
      audio.load()
    } else start()
  })
}
export async function prepareManagedAudioBuffer(buffer: ArrayBuffer): Promise<boolean> { return Boolean(await decodeManagedAudioBuffer(buffer)) || typeof URL.createObjectURL === 'function' }
export async function prepareManagedAudioUrl(src: string): Promise<boolean> {
  if (!src) return false
  const audio = getOrCreatePreparedAudio(src); attachAudioSource(audio, src)
  return waitForPreparedAudio(audio, src)
}
export async function warmupManagedAudio(): Promise<void> {
  const htmlWarmup = htmlAudioWarmupPromise ?? (htmlAudioWarmupPromise = warmupHtmlAudio())
  const audioContext = getOrCreateManagedAudioContext()
  const resumed = audioContext ? await resumeManagedAudioContext() : false
  await htmlWarmup
  if (resumed && audioContext?.state === 'running') await primeManagedAudioContextOutput(audioContext)
  ensureAudioUnlockListeners()
}
export async function playManagedAudioBuffer(buffer: ArrayBuffer, options: PlaybackOptions): Promise<boolean> {
  rememberManagedAudioFailureReason(null)
  const decodedBuffer = await decodeManagedAudioBuffer(buffer)
  if (decodedBuffer) {
    const startedFromWebAudio = await playWebAudioBuffer(decodedBuffer, options)
    if (startedFromWebAudio) return true
    if (getManagedAudioFailureReason() === 'not-allowed') return false
  }
  if (typeof URL.createObjectURL !== 'function') return false
  const objectUrl = URL.createObjectURL(new Blob([buffer], { type: 'audio/mpeg' }))
  return playHtmlAudio(objectUrl, {
    ...options,
    cleanup: () => {
      URL.revokeObjectURL(objectUrl)
      options.cleanup?.()
    },
  })
}
export function stopManagedAudio(): void {
  if (currentBufferSource) {
    currentBufferSource.onended = null
    try { currentBufferSource.stop(0) } catch {}
    try { currentBufferSource.disconnect() } catch {}
    currentBufferSource = null
  }
  if (currentBufferGain) {
    try { currentBufferGain.disconnect() } catch {}
    currentBufferGain = null
  }
  if (currentAudio) {
    currentAudio.onended = null
    currentAudio.onerror = null
    currentAudio.pause()
    currentAudio = null
  }
  cleanupPlayback()
}
export function playManagedAudioUrl(src: string, options: PlaybackOptions): Promise<boolean> { rememberManagedAudioFailureReason(null); return playHtmlAudio(src, options) }
export function __resetManagedAudioStateForTests(): void {
  stopManagedAudio()
  htmlAudioWarmupPromise = null
  audioOutputPrimed = false
  preparedAudioPool.clear()
  preparedAudioReadyPromises.clear()
  decodedBufferCache = new WeakMap()
  playbackReadyBufferCache = new WeakMap()
  clearAudioUnlockListeners()
  managedAudioOutputPrimed = false
  stopManagedAudioKeepAlive(managedAudioKeepAliveState)
  if (managedAudioContext && managedAudioContext.state !== 'closed') {
    void managedAudioContext.close().catch(() => {})
  }
  managedAudioContext = null
  managedAudioResumePromise = null
  managedAudioOutputPrimePromise = null
  resetManagedAudioFailureReason()
}
export function getManagedAudioLeadInMs(): number { return readManagedAudioLeadInMs(managedAudioContext && managedAudioContext.state !== 'closed' ? managedAudioContext : null) }
ensureAudioUnlockListeners()
