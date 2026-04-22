import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('../../lib', async () => {
  const actual = await vi.importActual<typeof import('../../lib')>('../../lib')
  return {
    ...actual,
    apiRequest: (url: string, options?: RequestInit) => globalThis.fetch(url, options),
    buildApiUrl: (path: string) => path,
  }
})

import { __resetAudioStateForTests, playWordAudio, stopAudio } from './utils'

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

describe('practice audio cache miss handling', () => {
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

  it('does not fall back to generated audio when the cached word audio is missing', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: false, headers: new Headers() })

    Object.defineProperty(globalThis, 'fetch', { value: fetchMock, writable: true })
    Object.defineProperty(globalThis, 'Audio', { value: TestAudio as unknown as typeof Audio, writable: true })
    Object.defineProperty(globalThis.URL, 'createObjectURL', { value: vi.fn(() => 'blob:missing'), writable: true })
    Object.defineProperty(globalThis.URL, 'revokeObjectURL', { value: vi.fn(), writable: true })

    const started = await playWordAudio('missing-word', { playbackSpeed: '1', volume: '100' }, undefined, { sourcePreference: 'url' })
    await flushAudioWork()

    expect(started).toBe(false)
    expect(fetchMock).toHaveBeenCalledTimes(3)
    expect(fetchMock).toHaveBeenNthCalledWith(1, '/api/tts/word-audio/metadata?w=missing-word', expect.objectContaining({
      method: 'GET',
      cache: 'no-store',
      headers: { 'Cache-Control': 'no-cache' },
    }))
    expect(fetchMock).toHaveBeenNthCalledWith(2, '/api/tts/word-audio?w=missing-word&cache_only=1', expect.objectContaining({
      method: 'GET',
      cache: 'no-store',
      headers: { 'Cache-Control': 'no-cache' },
      signal: expect.anything(),
    }))
    expect(fetchMock).toHaveBeenNthCalledWith(3, '/api/tts/word-audio?w=missing-word&cache_only=1', expect.objectContaining({
      method: 'GET',
      cache: 'no-store',
      headers: { 'Cache-Control': 'no-cache' },
      signal: expect.anything(),
    }))

    stopAudio()
  })

  it('does not promote cache fetch failures into generated word audio', async () => {
    const fetchMock = vi.fn().mockRejectedValue(new Error('network down'))

    Object.defineProperty(globalThis, 'fetch', { value: fetchMock, writable: true })
    Object.defineProperty(globalThis, 'Audio', { value: TestAudio as unknown as typeof Audio, writable: true })
    Object.defineProperty(globalThis.URL, 'createObjectURL', { value: vi.fn(() => 'blob:failed'), writable: true })
    Object.defineProperty(globalThis.URL, 'revokeObjectURL', { value: vi.fn(), writable: true })

    const started = await playWordAudio('cache-flaky', { playbackSpeed: '1', volume: '100' }, undefined, { sourcePreference: 'url' })
    await flushAudioWork()

    expect(started).toBe(false)
    expect(fetchMock).toHaveBeenCalledTimes(3)
    expect(fetchMock).toHaveBeenNthCalledWith(1, '/api/tts/word-audio/metadata?w=cache-flaky', expect.objectContaining({
      method: 'GET',
      cache: 'no-store',
      headers: { 'Cache-Control': 'no-cache' },
    }))
    expect(fetchMock).toHaveBeenNthCalledWith(2, '/api/tts/word-audio?w=cache-flaky&cache_only=1', expect.objectContaining({
      method: 'GET',
      cache: 'no-store',
      headers: { 'Cache-Control': 'no-cache' },
      signal: expect.anything(),
    }))
    expect(fetchMock).toHaveBeenNthCalledWith(3, '/api/tts/word-audio?w=cache-flaky&cache_only=1', expect.objectContaining({
      method: 'GET',
      cache: 'no-store',
      headers: { 'Cache-Control': 'no-cache' },
      signal: expect.anything(),
    }))

    stopAudio()
  })
})
