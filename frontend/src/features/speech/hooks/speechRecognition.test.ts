import { act, renderHook } from '@testing-library/react'
import { describe, expect, it, beforeEach, afterEach, vi } from 'vitest'
type SocketHandler = (...args: unknown[]) => void
const { mockSocket, ioMock } = vi.hoisted(() => {
  const socket = {
    connected: true,
    id: 'socket-1',
    handlers: new Map<string, SocketHandler[]>(),
    anyHandlers: [] as SocketHandler[],
    emit: vi.fn(),
    connect: vi.fn(),
    disconnect: vi.fn(),
    on(event: string, handler: SocketHandler) {
      const current = this.handlers.get(event) ?? []
      current.push(handler)
      this.handlers.set(event, current)
      return this
    },
    onAny(handler: SocketHandler) {
      this.anyHandlers.push(handler)
      return this
    },
    trigger(event: string, ...args: unknown[]) {
      for (const handler of this.handlers.get(event) ?? []) {
        handler(...args)
      }
      for (const handler of this.anyHandlers) {
        handler(event, ...args)
      }
    },
  }
  return {
    mockSocket: socket,
    ioMock: vi.fn(() => socket),
  }
})
vi.mock('socket.io-client', () => ({
  io: ioMock,
}))
const { useSpeechRecognition } = await import('./useSpeechRecognition')
function createMockGainNode() {
  return {
    connect: vi.fn(),
    disconnect: vi.fn(),
    gain: { value: 1 },
  }
}

describe('useSpeechRecognition', () => {
  const originalLocation = window.location
  const originalAudioContext = globalThis.AudioContext
  const originalMediaDevices = navigator.mediaDevices
  const originalWebkitSpeechRecognition = (
    window as Window & typeof globalThis & { webkitSpeechRecognition?: unknown }
  ).webkitSpeechRecognition
  let consoleLogSpy: ReturnType<typeof vi.spyOn>
  beforeEach(() => {
    vi.useFakeTimers()
    consoleLogSpy = vi.spyOn(console, 'log').mockImplementation(() => {})
    ioMock.mockClear()
    mockSocket.connect.mockClear()
    mockSocket.emit.mockClear()
    mockSocket.disconnect.mockClear()
    mockSocket.handlers.clear()
    mockSocket.anyHandlers = []
    mockSocket.connected = true
    mockSocket.id = 'socket-1'
    Object.defineProperty(window, 'location', {
      configurable: true,
      value: {
        protocol: 'https:',
        host: 'axiomaticworld.com',
        hostname: 'axiomaticworld.com',
        port: '',
      },
    })
  })
  afterEach(() => {
    vi.runOnlyPendingTimers()
    vi.useRealTimers()
    consoleLogSpy.mockRestore()
    Object.defineProperty(window, 'location', {
      configurable: true,
      value: originalLocation,
    })
    Object.defineProperty(globalThis, 'AudioContext', {
      configurable: true,
      value: originalAudioContext,
    })
    Object.defineProperty(navigator, 'mediaDevices', {
      configurable: true,
      value: originalMediaDevices,
    })
    Object.defineProperty(window, 'webkitSpeechRecognition', {
      configurable: true,
      value: originalWebkitSpeechRecognition,
    })
  })
  it('releases microphone resources when recognition completes', async () => {
    const trackStop = vi.fn()
    const getUserMedia = vi.fn()
    const stream = {
      getTracks: () => [{ stop: trackStop }],
    }
    const sourceConnect = vi.fn()
    const processorConnect = vi.fn()
    const processorDisconnect = vi.fn()
    const audioContextClose = vi.fn(() => Promise.resolve())
    const processor = {
      connect: processorConnect,
      disconnect: processorDisconnect,
      onaudioprocess: null as ((event: AudioProcessingEvent) => void) | null,
    }

    class MockAudioContext {
      destination = {}
      sampleRate = 48000
      state: AudioContextState = 'running'
      resume = vi.fn(() => Promise.resolve())
      close = audioContextClose
      createGain = vi.fn(() => createMockGainNode())
      createMediaStreamSource = vi.fn(() => ({
        connect: sourceConnect,
      }))
      createScriptProcessor = vi.fn(() => processor)
    }

    Object.defineProperty(globalThis, 'AudioContext', {
      configurable: true,
      value: MockAudioContext,
    })
    Object.defineProperty(navigator, 'mediaDevices', {
      configurable: true,
      value: {
        getUserMedia: getUserMedia.mockResolvedValue(stream),
      },
    })
    const { result } = renderHook(() => useSpeechRecognition({}))
    vi.runAllTimers()
    act(() => {
      mockSocket.trigger('connect')
    })
    await act(async () => {
      await result.current.startRecording()
    })
    expect(mockSocket.emit).toHaveBeenCalledWith('start_recognition', {
      language: 'zh',
      enable_vad: true,
      recognition_id: 1,
    })
    expect(getUserMedia).toHaveBeenCalledWith({
      audio: { channelCount: 1, autoGainControl: true, echoCancellation: true, noiseSuppression: true },
    })
    expect(sourceConnect).toHaveBeenCalledTimes(1)
    expect(processorConnect).toHaveBeenCalledTimes(1)
    act(() => {
      mockSocket.trigger('recognition_complete', { recognition_id: 1 })
    })
    expect(result.current.isRecording).toBe(false)
    expect(processorDisconnect).toHaveBeenCalledTimes(1)
    expect(audioContextClose).toHaveBeenCalledTimes(1)
    expect(trackStop).toHaveBeenCalledTimes(1)
  })

  it('switches into processing after stop and clears once a final result arrives', async () => {
    const stream = {
      getTracks: () => [{ stop: vi.fn() }],
    }
    const processor = {
      connect: vi.fn(),
      disconnect: vi.fn(),
      onaudioprocess: null as ((event: AudioProcessingEvent) => void) | null,
    }
    class MockAudioContext {
      destination = {}
      sampleRate = 48000
      state: AudioContextState = 'running'
      resume = vi.fn(() => Promise.resolve())
      close = vi.fn(() => Promise.resolve())
      createGain = vi.fn(() => createMockGainNode())
      createMediaStreamSource = vi.fn(() => ({
        connect: vi.fn(),
      }))
      createScriptProcessor = vi.fn(() => processor)
    }

    Object.defineProperty(globalThis, 'AudioContext', {
      configurable: true,
      value: MockAudioContext,
    })
    Object.defineProperty(navigator, 'mediaDevices', {
      configurable: true,
      value: {
        getUserMedia: vi.fn(() => Promise.resolve(stream)),
      },
    })
    const { result } = renderHook(() => useSpeechRecognition({}))
    vi.runAllTimers()
    act(() => {
      mockSocket.trigger('connect')
    })
    await act(async () => {
      await result.current.startRecording()
    })
    act(() => {
      const speechEvent = { inputBuffer: { getChannelData: () => new Float32Array(1024).fill(0.12) } } as AudioProcessingEvent
      processor.onaudioprocess?.(speechEvent)
      processor.onaudioprocess?.(speechEvent)
    })
    act(() => {
      result.current.stopRecording()
    })
    expect(result.current.isRecording).toBe(false)
    expect(result.current.isProcessing).toBe(true)
    expect(mockSocket.emit).toHaveBeenCalledWith('commit_audio_buffer')
    expect(mockSocket.emit).toHaveBeenCalledWith('stop_recognition')

    act(() => {
      mockSocket.trigger('recognition_stopped', { recognition_id: 1 })
    })
    expect(result.current.isProcessing).toBe(true)
    act(() => {
      mockSocket.trigger('final_result', { text: '你好', recognition_id: 1 })
    })

    expect(result.current.isProcessing).toBe(false)
  })

  it('surfaces a clear error when no microphone signal is captured', async () => {
    const stream = {
      getTracks: () => [{ stop: vi.fn() }],
    }
    const onError = vi.fn()

    class MockAudioContext {
      destination = {}
      sampleRate = 48000
      state: AudioContextState = 'running'
      resume = vi.fn(() => Promise.resolve())
      close = vi.fn(() => Promise.resolve())
      createGain = vi.fn(() => createMockGainNode())
      createMediaStreamSource = vi.fn(() => ({
        connect: vi.fn(),
      }))
      createScriptProcessor = vi.fn(() => ({
        connect: vi.fn(),
        disconnect: vi.fn(),
        onaudioprocess: null,
      }))
    }

    Object.defineProperty(globalThis, 'AudioContext', {
      configurable: true,
      value: MockAudioContext,
    })
    Object.defineProperty(navigator, 'mediaDevices', {
      configurable: true,
      value: {
        getUserMedia: vi.fn(() => Promise.resolve(stream)),
      },
    })

    const { result } = renderHook(() => useSpeechRecognition({ onError }))
    vi.runAllTimers()

    act(() => {
      mockSocket.trigger('connect')
    })

    await act(async () => {
      await result.current.startRecording()
    })

    act(() => {
      result.current.stopRecording()
      mockSocket.trigger('recognition_complete', { recognition_id: 1 })
    })

    expect(onError).toHaveBeenCalledWith('未检测到麦克风输入，请检查系统麦克风和浏览器权限')
    expect(result.current.isProcessing).toBe(false)
  })

  it('ignores late backend transcript events while idle', () => {
    const onPartial = vi.fn()
    const onResult = vi.fn()
    renderHook(() => useSpeechRecognition({ onPartial, onResult }))
    vi.runAllTimers()

    act(() => {
      mockSocket.trigger('connect')
      mockSocket.trigger('partial_result', { text: '嗯' })
      mockSocket.trigger('final_result', { text: '嗯。' })
    })

    expect(onPartial).not.toHaveBeenCalled()
    expect(onResult).not.toHaveBeenCalled()
  })

  it('ignores stale backend transcript events from an older recording session', async () => {
    const stream = {
      getTracks: () => [{ stop: vi.fn() }],
    }
    const onResult = vi.fn()

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

    Object.defineProperty(globalThis, 'AudioContext', {
      configurable: true,
      value: MockAudioContext,
    })
    Object.defineProperty(navigator, 'mediaDevices', {
      configurable: true,
      value: {
        getUserMedia: vi.fn(() => Promise.resolve(stream)),
      },
    })

    const { result } = renderHook(() => useSpeechRecognition({ onResult }))
    vi.runAllTimers()

    act(() => {
      mockSocket.trigger('connect')
    })

    await act(async () => {
      await result.current.startRecording()
    })

    act(() => {
      mockSocket.trigger('final_result', { text: '旧会话结果', recognition_id: 999 })
    })

    expect(onResult).not.toHaveBeenCalled()
    expect(result.current.isRecording).toBe(true)
  })

  it('falls back to browser speech recognition in browser-only mode', async () => {
    const stream = {
      getTracks: () => [{ stop: vi.fn() }],
    }
    const onResult = vi.fn()
    let recognitionInstance: {
      onresult: ((event: { resultIndex: number; results: Array<{ 0?: { transcript?: string }; isFinal?: boolean }> }) => void) | null
    } | null = null

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

      constructor() {
        recognitionInstance = this
      }
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

    Object.defineProperty(window, 'webkitSpeechRecognition', {
      configurable: true,
      value: MockRecognition,
    })
    Object.defineProperty(globalThis, 'AudioContext', {
      configurable: true,
      value: MockAudioContext,
    })
    Object.defineProperty(navigator, 'mediaDevices', {
      configurable: true,
      value: {
        getUserMedia: vi.fn(() => Promise.resolve(stream)),
      },
    })

    const { result } = renderHook(() => useSpeechRecognition({
      onResult,
      enableBrowserRecognition: true,
      enableRealtimeRecognition: false,
    }))
    vi.runAllTimers()

    act(() => {
      mockSocket.trigger('connect')
    })

    await act(async () => {
      await result.current.startRecording()
    })

    act(() => {
      recognitionInstance?.onresult?.({
        resultIndex: 0,
        results: [{ 0: { transcript: '浏览器兜底文本' }, isFinal: true }],
      })
    })

    expect(onResult).toHaveBeenCalledWith('浏览器兜底文本')
  })

  it('waits for browser final text before upload fallback in browser-only mode', async () => {
    const stream = {
      getTracks: () => [{ stop: vi.fn() }],
    }
    const onResult = vi.fn()
    let recognitionInstance: {
      onresult: ((event: { resultIndex: number; results: Array<{ 0?: { transcript?: string }; isFinal?: boolean }> }) => void) | null
    } | null = null

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

      constructor() {
        recognitionInstance = this
      }
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

    Object.defineProperty(window, 'webkitSpeechRecognition', {
      configurable: true,
      value: MockRecognition,
    })
    Object.defineProperty(globalThis, 'AudioContext', {
      configurable: true,
      value: MockAudioContext,
    })
    Object.defineProperty(navigator, 'mediaDevices', {
      configurable: true,
      value: {
        getUserMedia: vi.fn(() => Promise.resolve(stream)),
      },
    })

    const { result } = renderHook(() => useSpeechRecognition({
      onResult,
      enableBrowserRecognition: true,
      enableRealtimeRecognition: false,
    }))

    await act(async () => {
      await result.current.startRecording()
    })

    act(() => {
      result.current.stopRecording()
      recognitionInstance?.onresult?.({
        resultIndex: 0,
        results: [{ 0: { transcript: '浏览器最终文本' }, isFinal: true }],
      })
      vi.advanceTimersByTime(950)
    })

    expect(onResult).toHaveBeenCalledWith('浏览器最终文本')
    expect(result.current.isProcessing).toBe(false)
  })
})
