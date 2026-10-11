import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

type SocketHandler = (...args: unknown[]) => void

const { mockSocket, ioMock } = vi.hoisted(() => {
  const socket = {
    connected: true,
    handlers: new Map<string, SocketHandler[]>(),
    emit: vi.fn(),
    connect: vi.fn(),
    disconnect: vi.fn(),
    on(event: string, handler: SocketHandler) {
      const current = this.handlers.get(event) ?? []
      current.push(handler)
      this.handlers.set(event, current)
      return this
    },
    trigger(event: string, ...args: unknown[]) {
      for (const handler of this.handlers.get(event) ?? []) handler(...args)
    },
  }
  return { mockSocket: socket, ioMock: vi.fn(() => socket) }
})

vi.mock('socket.io-client', () => ({ io: ioMock }))

const { useSpeechRecognition } = await import('./useSpeechRecognition')

function createMockGainNode() {
  return { connect: vi.fn(), disconnect: vi.fn(), gain: { value: 1 } }
}

describe('useSpeechRecognition deferred browser fallback', () => {
  const originalLocation = window.location
  const originalAudioContext = globalThis.AudioContext
  const originalMediaDevices = navigator.mediaDevices
  const originalWebkitSpeechRecognition = (
    window as Window & typeof globalThis & { webkitSpeechRecognition?: unknown }
  ).webkitSpeechRecognition

  beforeEach(() => {
    ioMock.mockClear()
    mockSocket.handlers.clear()
    mockSocket.emit.mockClear()
    Object.defineProperty(window, 'location', {
      configurable: true,
      value: { protocol: 'https:', host: 'axiomaticworld.com', hostname: 'axiomaticworld.com', port: '' },
    })
  })

  afterEach(() => {
    Object.defineProperty(window, 'location', { configurable: true, value: originalLocation })
    Object.defineProperty(globalThis, 'AudioContext', { configurable: true, value: originalAudioContext })
    Object.defineProperty(navigator, 'mediaDevices', { configurable: true, value: originalMediaDevices })
    Object.defineProperty(window, 'webkitSpeechRecognition', { configurable: true, value: originalWebkitSpeechRecognition })
  })

  it('uses browser transcript as a deferred fallback in realtime mode', async () => {
    const stream = { getTracks: () => [{ stop: vi.fn() }] }
    const onResult = vi.fn()
    let recognitionInstance: { onresult: ((event: { resultIndex: number; results: Array<{ 0?: { transcript?: string }; isFinal?: boolean }> }) => void) | null } | null = null

    class MockRecognition {
      continuous = false
      interimResults = false
      lang = ''
      maxAlternatives = 0
      onend = null
      onerror = null
      onresult = null
      abort = vi.fn()
      start = vi.fn()
      stop = vi.fn()
      constructor() { recognitionInstance = this }
    }

    class MockAudioContext {
      destination = {}
      sampleRate = 48000
      state: AudioContextState = 'running'
      resume = vi.fn(() => Promise.resolve())
      close = vi.fn(() => Promise.resolve())
      createGain = vi.fn(() => createMockGainNode())
      createMediaStreamSource = vi.fn(() => ({ connect: vi.fn() }))
      createScriptProcessor = vi.fn(() => ({ connect: vi.fn(), disconnect: vi.fn(), onaudioprocess: null }))
    }

    Object.defineProperty(window, 'webkitSpeechRecognition', { configurable: true, value: MockRecognition })
    Object.defineProperty(globalThis, 'AudioContext', { configurable: true, value: MockAudioContext })
    Object.defineProperty(navigator, 'mediaDevices', { configurable: true, value: { getUserMedia: vi.fn(() => Promise.resolve(stream)) } })

    const { result } = renderHook(() => useSpeechRecognition({ onResult }))
    act(() => { mockSocket.trigger('connect') })
    await act(async () => { await result.current.startRecording() })
    act(() => { result.current.stopRecording() })
    act(() => {
      recognitionInstance?.onresult?.({
        resultIndex: 0,
        results: [{ 0: { transcript: '浏览器兜底文本' }, isFinal: true }],
      })
    })

    expect(onResult).toHaveBeenCalledWith('浏览器兜底文本')
    expect(result.current.isProcessing).toBe(false)
  })
})
