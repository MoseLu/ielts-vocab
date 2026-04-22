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
import { fillManagedAudioLeadIn } from './utils.audio.webAudio'

const createAudioResponse = (bytes: number[]) => ({
  ok: true,
  headers: new Headers({
    'X-Audio-Bytes': String(bytes.length),
    'X-Audio-Cache-Key': 'cache-v1',
  }),
  arrayBuffer: vi.fn().mockResolvedValue(new Uint8Array(bytes).buffer),
})

class TestAudio {
  src = ''
  readyState = 4
  currentTime = 0
  volume = 1
  playbackRate = 1
  onended: (() => void) | null = null
  onerror: (() => void) | null = null
  load = vi.fn()
  pause = vi.fn()
  addEventListener = vi.fn()
  play = vi.fn().mockResolvedValue(undefined)
}

class TestGainNode {
  gain = { value: 1 }
  connect = vi.fn()
  disconnect = vi.fn()
}

class TestConstantSourceNode {
  offset = { value: 0 }
  connect = vi.fn()
  disconnect = vi.fn()
  start = vi.fn()
  stop = vi.fn()
}

class TestBufferSourceNode {
  buffer: AudioBuffer | null = null
  loop = false
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
  currentTime = 0
  baseLatency = 0.03
  outputLatency = 0.02
  destination = {} as AudioDestinationNode
  bufferSources: TestBufferSourceNode[] = []
  constantSources: TestConstantSourceNode[] = []
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
  createBufferSource = vi.fn(() => {
    const node = new TestBufferSourceNode()
    this.bufferSources.push(node)
    return node as unknown as AudioBufferSourceNode
  })
  createConstantSource = vi.fn(() => {
    const node = new TestConstantSourceNode()
    this.constantSources.push(node)
    return node as unknown as ConstantSourceNode
  })
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

describe('managed web audio transport', () => {
  beforeEach(() => {
    __resetAudioStateForTests()
    TestManagedAudioContext.instances = []
    Object.defineProperty(globalThis, 'fetch', {
      value: vi.fn().mockResolvedValue(createAudioResponse([1, 2, 3])),
      writable: true,
    })
    Object.defineProperty(globalThis, 'Audio', { value: TestAudio as unknown as typeof Audio, writable: true })
    Object.defineProperty(globalThis, 'AudioContext', {
      value: TestManagedAudioContext as unknown as typeof AudioContext,
      writable: true,
      configurable: true,
    })
    Object.defineProperty(globalThis, 'webkitAudioContext', { value: undefined, writable: true, configurable: true })
    Object.defineProperty(globalThis.navigator, 'userActivation', {
      value: { isActive: true, hasBeenActive: true },
      writable: true,
      configurable: true,
    })
  })

  it('keeps the output awake and schedules buffered playback behind the latency-aware lead-in', async () => {
    const started = await playWordAudio('major', { playbackSpeed: '1', volume: '100' })
    await flushAudioWork()

    expect(started).toBe(true)
    const managedContext = TestManagedAudioContext.instances.at(-1)
    expect(managedContext?.createConstantSource).toHaveBeenCalledTimes(1)
    expect(managedContext?.constantSources.at(0)?.start).toHaveBeenCalledWith(0)
    expect(managedContext?.bufferSources.at(-1)?.start.mock.calls[0]?.[0]).toBe(0.1)

    stopAudio()
  })

  it('writes a non-zero warm-up lead-in before the decoded word samples', () => {
    const channelData = new Float32Array(8)

    fillManagedAudioLeadIn(channelData, 5, 0)

    expect(Array.from(channelData.slice(0, 5)).some(value => value !== 0)).toBe(true)
    expect(Array.from(channelData.slice(5)).every(value => value === 0)).toBe(true)
  })
})
