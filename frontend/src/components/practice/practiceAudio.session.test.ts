import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  __resetPracticeAudioSessionForTests,
  getPracticeAudioSnapshot,
  playPracticeAudio,
} from './practiceAudio.session'

class TestAudio {
  src = ''
  preload = 'auto'
  volume = 1
  playbackRate = 1
  currentTime = 0
  readyState = 4
  paused = true
  ended = false
  muted = false
  onended: (() => void) | null = null
  onerror: (() => void) | null = null
  load = vi.fn()
  pause = vi.fn(() => {
    this.paused = true
  })
  addEventListener = vi.fn()
  removeEventListener = vi.fn()
  play = vi.fn().mockImplementation(async () => {
    this.paused = false
  })
}

function createAudioResponse(cacheKey: string) {
  return {
    ok: true,
    headers: new Headers({
      'X-Audio-Bytes': '3',
      'X-Audio-Cache-Key': cacheKey,
    }),
    arrayBuffer: vi.fn().mockResolvedValue(new Uint8Array([1, 2, 3]).buffer),
  }
}

async function flushAudioWork() {
  for (let i = 0; i < 4; i += 1) await Promise.resolve()
  await new Promise(resolve => setTimeout(resolve, 0))
}

describe('practiceAudioSession', () => {
  beforeEach(() => {
    __resetPracticeAudioSessionForTests()
    Object.defineProperty(globalThis, 'Audio', { value: TestAudio as unknown as typeof Audio, writable: true })
    Object.defineProperty(globalThis.URL, 'createObjectURL', { value: vi.fn(() => 'blob:session-audio'), writable: true })
    Object.defineProperty(globalThis.URL, 'revokeObjectURL', { value: vi.fn(), writable: true })
    Object.defineProperty(globalThis, 'AudioContext', { value: undefined, writable: true, configurable: true })
    Object.defineProperty(globalThis, 'webkitAudioContext', { value: undefined, writable: true, configurable: true })
  })

  it('keeps the newest request as the active playback state when an older request resolves later', async () => {
    let resolveAlpha: ((value: unknown) => void) | null = null
    const fetchMock = vi.fn((url: string) => {
      if (url === '/api/tts/word-audio?w=alpha&cache_only=1') {
        return new Promise(resolve => {
          resolveAlpha = resolve
        })
      }
      if (url === '/api/tts/word-audio?w=beta&cache_only=1') {
        return Promise.resolve(createAudioResponse('beta-v1'))
      }
      return Promise.reject(new Error(`Unexpected request: ${url}`))
    })
    Object.defineProperty(globalThis, 'fetch', { value: fetchMock, writable: true })

    const alphaPromise = playPracticeAudio(
      { kind: 'word', word: 'alpha' },
      { playbackSpeed: '1', volume: '100' },
      { origin: 'session-test', wordKey: 'alpha', queueIndex: 0 },
    )
    const betaPromise = playPracticeAudio(
      { kind: 'word', word: 'beta' },
      { playbackSpeed: '1', volume: '100' },
      { origin: 'session-test', wordKey: 'beta', queueIndex: 1 },
    )

    resolveAlpha?.(createAudioResponse('alpha-v1'))
    await Promise.all([alphaPromise, betaPromise])
    await flushAudioWork()

    expect(getPracticeAudioSnapshot()).toMatchObject({
      state: 'playing',
      wordKey: 'beta',
      queueIndex: 1,
    })
  })

  it('publishes a blocked state when autoplay is rejected on the first url-based attempt', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue({
        byte_length: 3,
        cache_key: 'cache-v1',
        signed_url: 'https://oss.example.com/autoplay-blocked.mp3?signature=1',
      }),
    })
    class BlockingAudio extends TestAudio {
      play = vi.fn().mockRejectedValue(Object.assign(new Error('autoplay blocked'), { name: 'NotAllowedError' }))
    }

    Object.defineProperty(globalThis, 'fetch', { value: fetchMock, writable: true })
    Object.defineProperty(globalThis, 'Audio', { value: BlockingAudio as unknown as typeof Audio, writable: true })

    const started = await playPracticeAudio(
      { kind: 'word', word: 'autoplay-blocked', sourcePreference: 'url' },
      { playbackSpeed: '1', volume: '100' },
      { origin: 'session-test', wordKey: 'autoplay-blocked', queueIndex: 0, autoplay: true },
    )
    await flushAudioWork()

    expect(started).toBe(false)
    expect(getPracticeAudioSnapshot()).toMatchObject({
      state: 'blocked',
      wordKey: 'autoplay-blocked',
      queueIndex: 0,
      autoplay: true,
    })
  })
})
