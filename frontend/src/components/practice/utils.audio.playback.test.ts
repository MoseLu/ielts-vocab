import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  __resetManagedAudioStateForTests,
  playManagedAudioUrl,
  prepareManagedAudioUrl,
} from './utils.audio.playback'

type Listener = () => void

class LoadingAudio {
  static trackedLoads = 0

  src = ''
  preload = 'auto'
  volume = 1
  playbackRate = 1
  currentTime = 0
  readyState = 0
  networkState = 0
  muted = false
  paused = true
  ended = false
  onended: (() => void) | null = null
  onerror: (() => void) | null = null
  load = vi.fn(() => {
    if (this.src.startsWith('https://oss.example.com/')) LoadingAudio.trackedLoads += 1
    if (this.readyState >= 4) return
    setTimeout(() => {
      this.readyState = 4
      this.networkState = 1
      this.emit('loadeddata')
      this.emit('canplay')
      this.emit('canplaythrough')
    }, 0)
  })
  pause = vi.fn()
  play = vi.fn().mockImplementation(async () => {
    this.paused = false
  })

  private listeners = new Map<string, Set<Listener>>()

  constructor(src = '') {
    this.src = src
    if (src.startsWith('data:audio/wav')) {
      this.readyState = 4
      this.networkState = 1
    }
  }

  addEventListener = vi.fn((eventName: string, listener: Listener) => {
    const listeners = this.listeners.get(eventName) ?? new Set<Listener>()
    listeners.add(listener)
    this.listeners.set(eventName, listeners)
  })

  removeEventListener = vi.fn((eventName: string, listener: Listener) => {
    this.listeners.get(eventName)?.delete(listener)
  })

  private emit(eventName: string) {
    for (const listener of this.listeners.get(eventName) ?? []) listener()
  }
}

const playbackOptions = {
  isCurrent: () => true,
  isStopped: () => false,
  volume: 1,
  rate: 1,
}

describe('managed audio url preparation', () => {
  beforeEach(() => {
    __resetManagedAudioStateForTests()
    LoadingAudio.trackedLoads = 0
    Object.defineProperty(globalThis, 'Audio', {
      value: LoadingAudio as unknown as typeof Audio,
      writable: true,
      configurable: true,
    })
  })

  it('deduplicates concurrent prepares for the same OSS audio url', async () => {
    const url = 'https://oss.example.com/word.mp3?signature=1'

    const prepared = await Promise.all([
      prepareManagedAudioUrl(url),
      prepareManagedAudioUrl(url),
      prepareManagedAudioUrl(url),
    ])

    expect(prepared).toEqual([true, true, true])
    expect(LoadingAudio.trackedLoads).toBe(1)
  })

  it('reuses the in-flight prepare request when playback starts before preload settles', async () => {
    const url = 'https://oss.example.com/music.mp3?signature=1'

    const preparePromise = prepareManagedAudioUrl(url)
    const playPromise = playManagedAudioUrl(url, playbackOptions)

    await expect(Promise.all([preparePromise, playPromise])).resolves.toEqual([true, true])
    expect(LoadingAudio.trackedLoads).toBe(1)
  })

  it('does not reload a fresh prepared audio element before the first play', async () => {
    const url = 'https://oss.example.com/several.mp3?signature=1'

    await expect(prepareManagedAudioUrl(url)).resolves.toBe(true)
    await expect(playManagedAudioUrl(url, playbackOptions)).resolves.toBe(true)

    expect(LoadingAudio.trackedLoads).toBe(1)
  })
})
