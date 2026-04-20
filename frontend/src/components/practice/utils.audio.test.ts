import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  __resetAudioStateForTests,
  playExampleAudio,
  playSlowWordAudio,
  preloadWordAudio,
  preloadWordAudioBatch,
  playWordAudio,
  prepareWordAudioPlayback,
  stopAudio,
} from './utils'

const createAudioResponse = (bytes: number[], cacheKey = 'cache-v1') => ({
  ok: true,
  headers: new Headers({
    'X-Audio-Bytes': String(bytes.length),
    'X-Audio-Cache-Key': cacheKey,
  }),
  arrayBuffer: vi.fn().mockResolvedValue(new Uint8Array(bytes).buffer),
})

class TestAudio {
  src = ''
  volume = 1
  playbackRate = 1
  currentTime = 0
  duration = 0
  readyState = 4
  onended: (() => void) | null = null
  onerror: (() => void) | null = null
  load = vi.fn()
  pause = vi.fn()
  addEventListener = vi.fn()
  canPlayType = vi.fn(() => '')
  play = vi.fn().mockResolvedValue(undefined)
}

class TestGainNode {
  gain = { value: 1 }
  connect = vi.fn()
  disconnect = vi.fn()
}

class TestBufferSourceNode {
  buffer: AudioBuffer | null = null
  playbackRate = { value: 1 }
  onended: (() => void) | null = null
  connect = vi.fn()
  disconnect = vi.fn()
  start = vi.fn(() => {
    setTimeout(() => this.onended?.(), 0)
  })
  stop = vi.fn(() => {
    this.onended?.()
  })
}

class TestManagedAudioContext {
  static instances: TestManagedAudioContext[] = []

  state: AudioContextState = 'suspended'
  destination = {} as AudioDestinationNode
  resume = vi.fn(async () => {
    this.state = 'running'
  })
  decodeAudioData = vi.fn(async (buffer: ArrayBuffer) => ({
    duration: 1,
    length: Math.max(1, buffer.byteLength),
    numberOfChannels: 1,
    sampleRate: 24_000,
    getChannelData: vi.fn(() => new Float32Array(Math.max(1, buffer.byteLength))),
  } as unknown as AudioBuffer))
  createBuffer = vi.fn((_channels: number, length: number, sampleRate: number) => ({
    duration: length / Math.max(1, sampleRate),
    length,
    numberOfChannels: 1,
    sampleRate,
    getChannelData: vi.fn(() => new Float32Array(Math.max(1, length))),
  } as unknown as AudioBuffer))
  createGain = vi.fn(() => new TestGainNode() as unknown as GainNode)
  createBufferSource = vi.fn(() => new TestBufferSourceNode() as unknown as AudioBufferSourceNode)
  close = vi.fn(async () => {
    this.state = 'closed'
  })

  constructor() {
    TestManagedAudioContext.instances.push(this)
  }
}

async function flushAudioWork() {
  for (let i = 0; i < 4; i += 1) await Promise.resolve()
  await new Promise(resolve => setTimeout(resolve, 0))
  for (let i = 0; i < 4; i += 1) await Promise.resolve()
}

function expectWordAudioFetchCall(
  fetchMock: ReturnType<typeof vi.fn>,
  index: number,
  url: string,
  method: 'GET' | 'HEAD',
) {
  expect(fetchMock).toHaveBeenNthCalledWith(index, url, expect.objectContaining({
    method,
    cache: 'no-store',
    headers: { 'Cache-Control': 'no-cache' },
  }))
}

describe('practice audio cache', () => {
  const createObjectURLMock = vi.fn(() => 'blob:audio')
  const revokeObjectURLMock = vi.fn()

  beforeEach(() => {
    __resetAudioStateForTests()
    createObjectURLMock.mockClear()
    revokeObjectURLMock.mockClear()
    TestManagedAudioContext.instances = []
    Object.defineProperty(globalThis.URL, 'createObjectURL', { value: createObjectURLMock, writable: true })
    Object.defineProperty(globalThis.URL, 'revokeObjectURL', { value: revokeObjectURLMock, writable: true })
    Object.defineProperty(globalThis, 'AudioContext', { value: undefined, writable: true, configurable: true })
    Object.defineProperty(globalThis, 'webkitAudioContext', { value: undefined, writable: true, configurable: true })
    Object.defineProperty(globalThis.navigator, 'userActivation', {
      value: undefined,
      writable: true,
      configurable: true,
    })
  })

  it('preloads a full word audio buffer and reuses it on playback', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(createAudioResponse([1, 2, 3]))
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

    await preloadWordAudio('prefetched-word')
    playWordAudio('prefetched-word', { playbackSpeed: '1', volume: '100' })
    await flushAudioWork()

    expect(fetchMock).toHaveBeenCalledTimes(1)
    expectWordAudioFetchCall(fetchMock, 1, '/api/tts/word-audio?w=prefetched-word&cache_only=1', 'GET')
    expect(createObjectURLMock).toHaveBeenCalled()
    expect(createdAudioSources).toContain('blob:audio')
    stopAudio()
  })

  it('decodes preloaded word audio once and reuses the shared web audio path for playback', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(createAudioResponse([1, 2, 3]))
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
    Object.defineProperty(globalThis, 'AudioContext', {
      value: TestManagedAudioContext as unknown as typeof AudioContext,
      writable: true,
      configurable: true,
    })
    Object.defineProperty(globalThis.navigator, 'userActivation', {
      value: { isActive: true, hasBeenActive: true },
      writable: true,
      configurable: true,
    })

    const prepared = await prepareWordAudioPlayback('decoded-word')
    const firstStarted = await playWordAudio('decoded-word', { playbackSpeed: '1', volume: '100' })
    await flushAudioWork()
    const secondStarted = await playWordAudio('decoded-word', { playbackSpeed: '1', volume: '100' })
    await flushAudioWork()

    expect(prepared).toBe(true)
    expect(firstStarted).toBe(true)
    expect(secondStarted).toBe(true)
    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(createObjectURLMock).not.toHaveBeenCalled()
    expect(createdAudioSources).not.toContain('blob:audio')

    const managedContext = TestManagedAudioContext.instances.at(-1)
    expect(managedContext).toBeDefined()
    expect(managedContext?.decodeAudioData).toHaveBeenCalledTimes(1)
    expect(managedContext?.createBuffer).toHaveBeenCalledTimes(1)
    expect(managedContext?.createBufferSource).toHaveBeenCalledTimes(3)
    expect(managedContext?.resume).toHaveBeenCalled()

    stopAudio()
  })

  it('plays word audio from a fully fetched buffer on first playback', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(createAudioResponse([1, 2, 3]))
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

    playWordAudio('global', { playbackSpeed: '1', volume: '100' })
    await flushAudioWork()

    expect(fetchMock).toHaveBeenCalledTimes(1)
    expectWordAudioFetchCall(fetchMock, 1, '/api/tts/word-audio?w=global&cache_only=1', 'GET')
    expect(createdAudioSources.some(src => src.includes('dict.youdao.com'))).toBe(false)
    expect(createdAudioSources.some(src => src.includes('api.dictionaryapi.dev'))).toBe(false)
    expect(createObjectURLMock).toHaveBeenCalled()
    expect(createdAudioSources).toContain('blob:audio')

    stopAudio()
  })

  it('plays slow word audio through the regular word endpoint', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(createAudioResponse([1, 2, 3], 'cache-v1'))
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

    const started = await playSlowWordAudio('internet', { playbackSpeed: '1', volume: '100' }, '/ˈɪntənet/')
    await flushAudioWork()

    expect(started).toBe(true)
    expect(fetchMock).toHaveBeenCalledTimes(1)
    expectWordAudioFetchCall(fetchMock, 1, '/api/tts/word-audio?w=internet&cache_only=1', 'GET')
    expect(createdAudioSources.some(src => src.includes('pronunciation_mode=phonetic_segments'))).toBe(false)
    expect(createdAudioSources).toContain('blob:audio')

    stopAudio()
  })

  it('reuses the cached word buffer without revalidating metadata on repeated playback', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(createAudioResponse([1, 2, 3], 'cache-v1'))
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

    await preloadWordAudio('stale-word')
    playWordAudio('stale-word', { playbackSpeed: '1', volume: '100' })
    await flushAudioWork()

    expect(fetchMock).toHaveBeenCalledTimes(1)
    expectWordAudioFetchCall(fetchMock, 1, '/api/tts/word-audio?w=stale-word&cache_only=1', 'GET')
    expect(createdAudioSources).toContain('blob:audio')
    stopAudio()
  })

  it('drops mismatched cached example audio and refetches a complete copy', async () => {
    let now = 1_000
    const nowSpy = vi.spyOn(Date, 'now').mockImplementation(() => now)
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(createAudioResponse([1, 2, 3]))
      .mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ 'X-Audio-Bytes': '4', 'X-Audio-Cache-Key': 'cache-v2' }),
      })
      .mockResolvedValueOnce(createAudioResponse([7, 8, 9, 10]))

    Object.defineProperty(globalThis, 'fetch', { value: fetchMock, writable: true })
    Object.defineProperty(globalThis, 'Audio', { value: TestAudio as unknown as typeof Audio, writable: true })
    playExampleAudio('Example sentence', 'alpha', { playbackSpeed: '1', volume: '100' })
    await flushAudioWork()
    now += 6_000
    playExampleAudio('Example sentence', 'alpha', { playbackSpeed: '1', volume: '100' })
    await flushAudioWork()

    expect(fetchMock).toHaveBeenNthCalledWith(2, '/api/tts/example-audio', {
      method: 'POST',
      cache: 'no-store',
      headers: {
        'Cache-Control': 'no-cache',
        'Content-Type': 'application/json',
        'X-Audio-Metadata-Only': '1',
      },
      body: JSON.stringify({ sentence: 'Example sentence', word: 'alpha' }),
    })
    expect(fetchMock).toHaveBeenNthCalledWith(3, '/api/tts/example-audio', {
      method: 'POST',
      cache: 'no-store',
      headers: {
        'Cache-Control': 'no-cache',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ sentence: 'Example sentence', word: 'alpha' }),
    })
    expect(createObjectURLMock).toHaveBeenCalled()

    nowSpy.mockRestore()
    stopAudio()
  })

  it('plays cached OSS-backed word audio through the same cache-only endpoint', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(createAudioResponse([1, 2, 3], 'oss-cache-v1'))
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

    playWordAudio('oss-word', { playbackSpeed: '1', volume: '100' })
    await flushAudioWork()

    expect(fetchMock).toHaveBeenCalledTimes(1)
    expectWordAudioFetchCall(fetchMock, 1, '/api/tts/word-audio?w=oss-word&cache_only=1', 'GET')
    expect(createdAudioSources.every(src => !src.includes('oss.example.com'))).toBe(true)
    expect(createdAudioSources).toContain('blob:audio')
    expect(createObjectURLMock).toHaveBeenCalled()

    stopAudio()
  })

  it('preloads several upcoming words without duplicating the same word request', async () => {
    const fetchMock = vi.fn((url: string, init?: RequestInit) => {
      const method = init?.method ?? 'GET'
      if (url === '/api/tts/word-audio?w=alpha&cache_only=1' && method === 'GET') {
        return Promise.resolve(createAudioResponse([1, 2, 3], 'alpha-v1'))
      }
      if (url === '/api/tts/word-audio?w=beta&cache_only=1' && method === 'GET') {
        return Promise.resolve(createAudioResponse([4, 5, 6, 7], 'beta-v1'))
      }
      return Promise.reject(new Error(`Unexpected request: ${method} ${url}`))
    })

    Object.defineProperty(globalThis, 'fetch', { value: fetchMock, writable: true })
    Object.defineProperty(globalThis, 'Audio', { value: TestAudio as unknown as typeof Audio, writable: true })

    await preloadWordAudioBatch(['alpha', 'alpha', 'beta'], 3)

    const alphaCalls = fetchMock.mock.calls.filter(([url]) => String(url).includes('/api/tts/word-audio?w=alpha'))
    const betaCalls = fetchMock.mock.calls.filter(([url]) => String(url).includes('/api/tts/word-audio?w=beta'))
    expect(alphaCalls.filter(([, init]) => (init as RequestInit | undefined)?.method === 'GET').length).toBe(1)
    expect(betaCalls.filter(([, init]) => (init as RequestInit | undefined)?.method === 'GET').length).toBe(1)
  })

  it('uses the latest cache key in the direct example playback URL when blob URLs are unavailable', async () => {
    const fetchMock = vi.fn().mockResolvedValue(createAudioResponse([1, 2, 3], 'cache-v3'))
    const createdAudioSources: string[] = []

    class TrackingAudio extends TestAudio {
      constructor(src = '') {
        super()
        this.src = src
        createdAudioSources.push(src)
      }
    }

    Object.defineProperty(globalThis.URL, 'createObjectURL', { value: undefined, writable: true })
    Object.defineProperty(globalThis, 'fetch', { value: fetchMock, writable: true })
    Object.defineProperty(globalThis, 'Audio', { value: TrackingAudio as unknown as typeof Audio, writable: true })

    playExampleAudio('Example sentence', 'alpha', { playbackSpeed: '1', volume: '100' })
    await flushAudioWork()

    expect(fetchMock).toHaveBeenCalledOnce()
    stopAudio()
  })
})
