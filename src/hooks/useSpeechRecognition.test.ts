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

describe('useSpeechRecognition', () => {
  const originalLocation = window.location
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
  })

  it('does not emit debug logs during normal socket setup and ready events', () => {
    renderHook(() => useSpeechRecognition({}))
    vi.runAllTimers()

    act(() => {
      mockSocket.trigger('connect')
      mockSocket.trigger('connected', { api_configured: true })
      mockSocket.trigger('recognition_started', { session_id: 'session-1' })
    })

    expect(ioMock).toHaveBeenCalledWith(
      'wss://axiomaticworld.com/speech',
      expect.objectContaining({ autoConnect: false })
    )
    expect(mockSocket.connect).toHaveBeenCalledTimes(1)
    expect(consoleLogSpy).not.toHaveBeenCalled()
  })

  it('connects directly to the speech service in local vite dev mode', () => {
    Object.defineProperty(window, 'location', {
      configurable: true,
      value: {
        protocol: 'http:',
        host: 'localhost:3020',
        hostname: 'localhost',
        port: '3020',
      },
    })

    renderHook(() => useSpeechRecognition({}))
    vi.runAllTimers()

    expect(ioMock).toHaveBeenCalledWith(
      'ws://localhost:5001/speech',
      expect.objectContaining({ autoConnect: false })
    )
    expect(mockSocket.connect).toHaveBeenCalledTimes(1)
  })

  it('does not create a socket connection when disabled', () => {
    renderHook(() => useSpeechRecognition({ enabled: false }))

    expect(ioMock).not.toHaveBeenCalled()
    expect(mockSocket.disconnect).not.toHaveBeenCalled()
  })
})
