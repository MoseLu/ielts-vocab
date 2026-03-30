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
    consoleLogSpy = vi.spyOn(console, 'log').mockImplementation(() => {})
    ioMock.mockClear()
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
      },
    })
  })

  afterEach(() => {
    consoleLogSpy.mockRestore()
    Object.defineProperty(window, 'location', {
      configurable: true,
      value: originalLocation,
    })
  })

  it('does not emit debug logs during normal socket setup and ready events', () => {
    renderHook(() => useSpeechRecognition({}))

    act(() => {
      mockSocket.trigger('connect')
      mockSocket.trigger('connected', { api_configured: true })
      mockSocket.trigger('recognition_started', { session_id: 'session-1' })
    })

    expect(ioMock).toHaveBeenCalledWith('wss://axiomaticworld.com/speech', expect.any(Object))
    expect(consoleLogSpy).not.toHaveBeenCalled()
  })
})
