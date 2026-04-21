import { beforeEach, describe, expect, it, vi } from 'vitest'
import { __resetAudioStateForTests, playWordAudio, stopAudio } from './utils'

class BlockingAudio {
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
  play = vi.fn().mockRejectedValue(Object.assign(new Error('autoplay blocked'), { name: 'NotAllowedError' }))
}

async function flushAudioWork() {
  for (let i = 0; i < 4; i += 1) await Promise.resolve()
  await new Promise(resolve => setTimeout(resolve, 0))
}

describe('practice audio autoplay blocking', () => {
  beforeEach(() => {
    __resetAudioStateForTests()
    Object.defineProperty(globalThis, 'fetch', {
      value: vi.fn().mockResolvedValue({
        ok: true,
        json: vi.fn().mockResolvedValue({
          byte_length: 3,
          cache_key: 'cache-v1',
          signed_url: 'https://oss.example.com/autoplay-blocked.mp3?signature=1',
        }),
      }),
      writable: true,
    })
    Object.defineProperty(globalThis, 'Audio', { value: BlockingAudio as unknown as typeof Audio, writable: true })
    Object.defineProperty(globalThis.URL, 'createObjectURL', { value: vi.fn(() => 'blob:blocked'), writable: true })
    Object.defineProperty(globalThis.URL, 'revokeObjectURL', { value: vi.fn(), writable: true })
    Object.defineProperty(globalThis, 'AudioContext', { value: undefined, writable: true, configurable: true })
    Object.defineProperty(globalThis, 'webkitAudioContext', { value: undefined, writable: true, configurable: true })
  })

  it('does not fall back to blob playback when autoplay is blocked for an OSS URL', async () => {
    const started = await playWordAudio('autoplay-blocked', { playbackSpeed: '1', volume: '100' }, undefined, { sourcePreference: 'url' })
    await flushAudioWork()

    expect(started).toBe(false)
    expect(globalThis.fetch).toHaveBeenCalledTimes(1)
    expect(globalThis.fetch).toHaveBeenNthCalledWith(1, '/api/tts/word-audio/metadata?w=autoplay-blocked', expect.objectContaining({
      method: 'GET',
      cache: 'no-store',
      headers: { 'Cache-Control': 'no-cache' },
    }))
    expect(globalThis.URL.createObjectURL).not.toHaveBeenCalled()

    stopAudio()
  })
})
