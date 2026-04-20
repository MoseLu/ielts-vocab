import { beforeEach, describe, expect, it, vi } from 'vitest'
import { __resetAudioStateForTests, playWordAudio, stopAudio } from './utils'

const createAudioResponse = (bytes: number[]) => ({
  ok: true,
  headers: new Headers({
    'X-Audio-Bytes': String(bytes.length),
    'X-Audio-Cache-Key': 'generated-v1',
  }),
  arrayBuffer: vi.fn().mockResolvedValue(new Uint8Array(bytes).buffer),
})

class TestAudio {
  src = ''
  volume = 1
  playbackRate = 1
  currentTime = 0
  readyState = 4
  onended: (() => void) | null = null
  onerror: (() => void) | null = null
  load = vi.fn()
  pause = vi.fn()
  addEventListener = vi.fn()
  play = vi.fn().mockResolvedValue(undefined)
}

async function flushAudioWork() {
  for (let i = 0; i < 4; i += 1) await Promise.resolve()
  await new Promise(resolve => setTimeout(resolve, 0))
}

describe('practice audio cache miss fallback', () => {
  beforeEach(() => {
    __resetAudioStateForTests()
    Object.defineProperty(globalThis, 'AudioContext', { value: undefined, writable: true, configurable: true })
    Object.defineProperty(globalThis, 'webkitAudioContext', { value: undefined, writable: true, configurable: true })
    Object.defineProperty(globalThis.navigator, 'userActivation', {
      value: undefined,
      writable: true,
      configurable: true,
    })
  })

  it('falls back to generated word audio when cache metadata is missing', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({ ok: false, headers: new Headers() })
      .mockResolvedValueOnce(createAudioResponse([1, 2, 3]))
    const createObjectURLMock = vi.fn(() => 'blob:generated')
    const createdAudioSources: string[] = []

    class TrackingAudio extends TestAudio {
      constructor(src = '') {
        super()
        this.src = src
        createdAudioSources.push(src)
      }
    }

    Object.defineProperty(globalThis, 'fetch', { value: fetchMock, writable: true })
    Object.defineProperty(globalThis, 'Audio', { value: TrackingAudio as unknown as typeof Audio, writable: true })
    Object.defineProperty(globalThis.URL, 'createObjectURL', { value: createObjectURLMock, writable: true })
    Object.defineProperty(globalThis.URL, 'revokeObjectURL', { value: vi.fn(), writable: true })

    const started = await playWordAudio('generated-word', { playbackSpeed: '1', volume: '100' })
    await flushAudioWork()

    expect(started).toBe(true)
    expect(fetchMock).toHaveBeenNthCalledWith(1, '/api/tts/word-audio?w=generated-word&cache_only=1', expect.objectContaining({
      method: 'HEAD',
      cache: 'no-store',
      headers: { 'Cache-Control': 'no-cache' },
      signal: expect.anything(),
    }))
    expect(fetchMock).toHaveBeenNthCalledWith(2, '/api/tts/word-audio?w=generated-word', {
      method: 'GET',
      cache: 'no-store',
      headers: { 'Cache-Control': 'no-cache' },
    })
    expect(createObjectURLMock).toHaveBeenCalled()
    expect(createdAudioSources).toContain('blob:generated')

    stopAudio()
  })

  it('falls back to generated word audio when cached content fetch fails', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        headers: new Headers({
          'X-Audio-Bytes': '5',
          'X-Audio-Cache-Key': 'cached-v1',
        }),
      })
      .mockResolvedValueOnce({ ok: false, headers: new Headers() })
      .mockResolvedValueOnce({ ok: false, headers: new Headers() })
      .mockResolvedValueOnce(createAudioResponse([4, 5, 6]))
    const createObjectURLMock = vi.fn(() => 'blob:recovered')
    const createdAudioSources: string[] = []

    class TrackingAudio extends TestAudio {
      constructor(src = '') {
        super()
        this.src = src
        createdAudioSources.push(src)
      }
    }

    Object.defineProperty(globalThis, 'fetch', { value: fetchMock, writable: true })
    Object.defineProperty(globalThis, 'Audio', { value: TrackingAudio as unknown as typeof Audio, writable: true })
    Object.defineProperty(globalThis.URL, 'createObjectURL', { value: createObjectURLMock, writable: true })
    Object.defineProperty(globalThis.URL, 'revokeObjectURL', { value: vi.fn(), writable: true })

    const started = await playWordAudio('cache-flaky', { playbackSpeed: '1', volume: '100' })
    await flushAudioWork()

    expect(started).toBe(true)
    expect(fetchMock).toHaveBeenNthCalledWith(1, '/api/tts/word-audio?w=cache-flaky&cache_only=1', expect.objectContaining({
      method: 'HEAD',
      cache: 'no-store',
      headers: { 'Cache-Control': 'no-cache' },
      signal: expect.anything(),
    }))
    expect(fetchMock).toHaveBeenNthCalledWith(2, '/api/tts/word-audio?w=cache-flaky&cache_only=1&v=cached-v1', expect.objectContaining({
      method: 'GET',
      cache: 'no-store',
      headers: { 'Cache-Control': 'no-cache' },
      signal: expect.anything(),
    }))
    expect(fetchMock).toHaveBeenNthCalledWith(3, '/api/tts/word-audio?w=cache-flaky&cache_only=1&v=cached-v1', expect.objectContaining({
      method: 'GET',
      cache: 'no-store',
      headers: { 'Cache-Control': 'no-cache' },
      signal: expect.anything(),
    }))
    expect(fetchMock).toHaveBeenNthCalledWith(4, '/api/tts/word-audio?w=cache-flaky', {
      method: 'GET',
      cache: 'no-store',
      headers: { 'Cache-Control': 'no-cache' },
    })
    expect(createObjectURLMock).toHaveBeenCalled()
    expect(createdAudioSources).toContain('blob:recovered')

    stopAudio()
  })
})
