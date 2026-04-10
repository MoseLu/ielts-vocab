import { describe, it, expect, beforeEach, vi } from 'vitest'
import { act, renderHook } from '@testing-library/react'
import { useAIChat } from './useAIChat'
import { clearGlobalLearningContext } from '../contexts/AIChatContext'


const greetingAudioMocks = vi.hoisted(() => ({
  play: vi.fn(() => Promise.resolve(true)),
  stop: vi.fn(),
  warmup: vi.fn(() => Promise.resolve()),
}))

vi.mock('../composables/ai-chat/greetingAudio', () => ({
  playAIGreetingAudio: greetingAudioMocks.play,
  stopAIGreetingAudio: greetingAudioMocks.stop,
  warmupAIGreetingAudio: greetingAudioMocks.warmup,
}))


beforeEach(() => {
  localStorage.clear()
  clearGlobalLearningContext()
  vi.clearAllMocks()
})


describe('useAIChat greeting refresh', () => {
  it('refreshes the greeting when reopening before any user message is sent', async () => {
    const mockFetch = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ reply: '第一条问候。' }), { status: 200, headers: { 'Content-Type': 'application/json' } }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ reply: '第二条问候。' }), { status: 200, headers: { 'Content-Type': 'application/json' } }))
    vi.stubGlobal('fetch', mockFetch)

    const { result } = renderHook(() => useAIChat())

    await act(async () => {
      await result.current.openPanel()
    })

    expect(result.current.messages[0]?.content).toBe('第一条问候。')

    await act(async () => {
      result.current.closePanel()
    })

    await act(async () => {
      await result.current.openPanel()
    })

    expect(mockFetch).toHaveBeenCalledTimes(2)
    expect(mockFetch.mock.calls[0][0]).toBe('/api/ai/greet')
    expect(mockFetch.mock.calls[1][0]).toBe('/api/ai/greet')
    expect(result.current.messages[0]?.content).toBe('第二条问候。')
    vi.restoreAllMocks()
  })
})
