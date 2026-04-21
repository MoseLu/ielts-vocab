import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import FollowMode from './FollowMode'
import type { Word } from './types'

const fetchFollowReadWordMock = vi.fn()
const fetchMock = vi.fn()

vi.mock('./followReadApi', () => ({
  fetchFollowReadWord: (...args: unknown[]) => fetchFollowReadWordMock(...args),
}))

class TestAudio {
  static instances: TestAudio[] = []

  src = ''
  preload = 'auto'
  volume = 1
  playbackRate = 1
  currentTime = 0.36
  duration = 1.4
  paused = true
  ended = false
  onended: (() => void) | null = null
  onerror: (() => void) | null = null
  onloadedmetadata: (() => void) | null = null
  load = vi.fn()
  play = vi.fn(async () => {
    this.paused = false
    this.onloadedmetadata?.()
  })
  pause = vi.fn(() => {
    this.paused = true
  })

  constructor(src = '') {
    this.src = src
    TestAudio.instances.push(this)
  }
}

function makeWord(): Word {
  return {
    word: 'phenomenon',
    phonetic: '/fəˈnɒmɪnən/',
    pos: 'n.',
    definition: '现象；迹象；非凡的人',
  }
}

describe('FollowMode', () => {
  beforeEach(() => {
    fetchFollowReadWordMock.mockReset()
    fetchMock.mockReset()
    TestAudio.instances = []
    Object.defineProperty(globalThis, 'fetch', {
      value: fetchMock.mockResolvedValue({
        ok: true,
        headers: new Headers({ 'X-Audio-Bytes': '3', 'X-Audio-Cache-Key': 'follow-v1' }),
        arrayBuffer: vi.fn().mockResolvedValue(new Uint8Array([1, 2, 3]).buffer),
      }),
      writable: true,
    })
    Object.defineProperty(globalThis, 'Audio', { value: TestAudio as unknown as typeof Audio, writable: true })
    Object.defineProperty(globalThis.URL, 'createObjectURL', { value: vi.fn(() => 'blob:follow-audio'), writable: true })
    Object.defineProperty(globalThis.URL, 'revokeObjectURL', { value: vi.fn(), writable: true })
    Object.defineProperty(globalThis, 'AudioContext', { value: undefined, writable: true, configurable: true })
    Object.defineProperty(globalThis, 'webkitAudioContext', { value: undefined, writable: true, configurable: true })
    Object.defineProperty(window, 'requestAnimationFrame', { value: vi.fn(() => 1), writable: true })
    Object.defineProperty(window, 'cancelAnimationFrame', { value: vi.fn(), writable: true })
  })

  it('renders follow-read segments and plays the merged follow-read track', async () => {
    fetchFollowReadWordMock.mockResolvedValue({
      word: 'phenomenon',
      phonetic: '/fəˈnɒmɪnən/',
      definition: '现象；迹象；非凡的人',
      pos: 'n.',
      audio_url: '/api/tts/word-audio?w=phenomenon',
      audio_profile: 'full_chunk_full',
      audio_playback_rate: 1,
      chunk_audio_url: '/api/tts/follow-read-chunked-audio?w=phenomenon&phonetic=%2Ff%C9%99%CB%88n%C9%92m%C9%AAn%C9%99n%2F',
      chunk_audio_profile: 'full_chunk_full_merged',
      estimated_duration_ms: 5600,
      audio_sequence: [
        { id: 'follow-read-track', kind: 'follow', label: '完整示范 -> 拆分跟读 -> 完整回放', url: '/api/tts/follow-read-chunked-audio?w=phenomenon&phonetic=%2Ff%C9%99%CB%88n%C9%92m%C9%AAn%C9%99n%2F', playback_rate: 1, track_segments: true },
      ],
      segments: [
        { id: 'seg-0', letter_start: 0, letter_end: 3, letters: 'phe', phonetic: 'fə', start_ms: 1000, end_ms: 1280 },
        { id: 'seg-1', letter_start: 3, letter_end: 5, letters: 'no', phonetic: 'nə', start_ms: 2080, end_ms: 2560 },
        { id: 'seg-2', letter_start: 5, letter_end: 7, letters: 'me', phonetic: 'mɪ', start_ms: 3360, end_ms: 3640 },
        { id: 'seg-3', letter_start: 7, letter_end: 10, letters: 'non', phonetic: 'nən', start_ms: 4440, end_ms: 4720 },
      ],
    })

    const user = userEvent.setup()
    const onSessionInteraction = vi.fn(() => Promise.resolve())
    const onStartRecording = vi.fn(() => Promise.resolve())

    render(
      <FollowMode
        currentWord={makeWord()}
        queueIndex={0}
        total={3}
        settings={{ volume: '60' }}
        speechConnected
        speechRecording={false}
        recognizedText="phenomenon"
        favoriteSlot={<button type="button">fav</button>}
        onIndexChange={vi.fn()}
        onCompleteSession={vi.fn(() => Promise.resolve())}
        onStartRecording={onStartRecording}
        onStopRecording={vi.fn()}
        onSessionInteraction={onSessionInteraction}
      />,
    )

    await waitFor(() => {
      expect(fetchFollowReadWordMock).toHaveBeenCalledWith(makeWord())
      expect(fetchMock).toHaveBeenCalled()
    })

    expect(await screen.findByText('/fə/')).toBeInTheDocument()
    expect(screen.getByText('/nə/')).toBeInTheDocument()
    expect(screen.getByText('现象；迹象；非凡的人')).toBeInTheDocument()
    expect(screen.getByText('fav')).toBeInTheDocument()
    expect(screen.getByText('识别结果：phenomenon')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: '播放' }))

    await waitFor(() => {
      expect(onSessionInteraction).toHaveBeenCalled()
      expect(TestAudio.instances.some(instance => instance.play.mock.calls.length > 0)).toBe(true)
    })

    expect(fetchMock.mock.calls.some(([url]) => String(url).includes('/api/tts/follow-read-chunked-audio'))).toBe(true)

    await user.click(screen.getByRole('button', { name: '录音' }))
    await waitFor(() => {
      expect(onStartRecording).toHaveBeenCalled()
    })
  })

  it('completes the session on the last word', async () => {
    fetchFollowReadWordMock.mockResolvedValue({
      word: 'phenomenon',
      phonetic: '/fəˈnɒmɪnən/',
      definition: '现象',
      pos: 'n.',
      audio_url: '/api/tts/word-audio?w=phenomenon',
      audio_profile: 'full_chunk_full',
      audio_playback_rate: 1,
      chunk_audio_url: '/api/tts/follow-read-chunked-audio?w=phenomenon&phonetic=%2Ff%C9%99%CB%88n%C9%92m%C9%AAn%C9%99n%2F',
      chunk_audio_profile: 'full_chunk_full_merged',
      estimated_duration_ms: 4200,
      audio_sequence: [
        { id: 'follow-read-track', kind: 'follow', label: '完整示范 -> 拆分跟读 -> 完整回放', url: '/api/tts/follow-read-chunked-audio?w=phenomenon&phonetic=%2Ff%C9%99%CB%88n%C9%92m%C9%AAn%C9%99n%2F', playback_rate: 1, track_segments: true },
      ],
      segments: [{ id: 'seg-0', letter_start: 0, letter_end: 10, letters: 'phenomenon', phonetic: 'fəˈnɒmɪnən', start_ms: 950, end_ms: 2400 }],
    })

    const user = userEvent.setup()
    const onCompleteSession = vi.fn(() => Promise.resolve())
    const onIndexChange = vi.fn()

    render(
      <FollowMode
        currentWord={makeWord()}
        queueIndex={1}
        total={2}
        settings={{}}
        speechConnected={false}
        speechRecording={false}
        recognizedText=""
        onIndexChange={onIndexChange}
        onCompleteSession={onCompleteSession}
        onStartRecording={vi.fn(() => Promise.resolve())}
        onStopRecording={vi.fn()}
        onSessionInteraction={vi.fn(() => Promise.resolve())}
      />,
    )

    await screen.findByText('/fəˈnɒmɪnən/')
    await user.click(screen.getByRole('button', { name: '完成' }))

    await waitFor(() => {
      expect(onCompleteSession).toHaveBeenCalled()
      expect(onIndexChange).toHaveBeenCalledWith(2)
    })
  })
})
