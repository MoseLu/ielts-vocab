import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import FollowMode from './FollowMode'
import type { Word } from './types'

const fetchFollowReadWordMock = vi.fn()
const evaluateFollowReadPronunciationMock = vi.fn()
const explainFollowReadPronunciationMock = vi.fn()
const fetchMock = vi.fn()
const audioSessionMock = vi.hoisted(() => ({
  lastOnEnd: null as (() => void) | null,
  listeners: new Set<(value: Record<string, unknown>) => void>(),
  play: vi.fn(),
  prepare: vi.fn(),
  stop: vi.fn(),
}))
const recorderMock = vi.hoisted(() => ({
  emitLevel: (_level: number) => {},
  nextStopBlob: new Blob(['voice'], { type: 'audio/wav' }) as Blob | null,
  reset: vi.fn(),
  start: vi.fn(),
  stop: vi.fn(),
}))
const waveformMock = vi.hoisted(() => ({
  attachCanvas: vi.fn(),
  pushAmplitude: vi.fn(),
  resetWaveform: vi.fn(),
  setWaveformRecordingState: vi.fn(),
}))

vi.mock('../../features/practice/audio/followReadApi', () => ({
  fetchFollowReadWord: (...args: unknown[]) => fetchFollowReadWordMock(...args),
}))

vi.mock('./followReadScoring', () => ({
  evaluateFollowReadPronunciation: (...args: unknown[]) => evaluateFollowReadPronunciationMock(...args),
  explainFollowReadPronunciation: (...args: unknown[]) => explainFollowReadPronunciationMock(...args),
}))

vi.mock('./practiceAudio.session', () => {
  const idleSnapshot = {
    state: 'idle',
    requestId: null,
    origin: null,
    wordKey: null,
    queueIndex: null,
    autoplay: false,
    assetId: null,
    clipIndex: -1,
    clipCount: 0,
    currentTimeMs: 0,
    durationMs: null,
    error: null,
  }
  return {
    getPracticeAudioSnapshot: () => idleSnapshot,
    preparePracticeAudio: (...args: unknown[]) => {
      audioSessionMock.prepare(...args)
      return Promise.resolve(true)
    },
    playPracticeAudio: (...args: unknown[]) => {
      const context = args[2] as { origin?: string; wordKey?: string; queueIndex?: number }
      const options = args[3] as { onEnd?: () => void } | undefined
      audioSessionMock.lastOnEnd = options?.onEnd ?? null
      audioSessionMock.play(...args)
      audioSessionMock.listeners.forEach(listener => listener({
        ...idleSnapshot,
        state: 'playing',
        origin: context.origin,
        wordKey: context.wordKey,
        queueIndex: context.queueIndex,
        clipIndex: 0,
        clipCount: 1,
        currentTimeMs: 0,
        durationMs: 1000,
      }))
      return Promise.resolve(true)
    },
    stopPracticeAudio: () => {
      audioSessionMock.stop()
      audioSessionMock.listeners.forEach(listener => listener(idleSnapshot))
    },
    subscribePracticeAudio: (listener: (value: Record<string, unknown>) => void) => {
      audioSessionMock.listeners.add(listener)
      listener(idleSnapshot)
      return () => audioSessionMock.listeners.delete(listener)
    },
  }
})

vi.mock('../../features/speech/hooks/useSpeakingRecorder', async () => {
  const React = await vi.importActual<typeof import('react')>('react')
  return {
    default: () => {
      const [state, setState] = React.useState({
        durationSeconds: 0,
        error: null as string | null,
        isRecording: false,
        level: 0,
      })
      recorderMock.emitLevel = (level: number) => setState(current => ({ ...current, level }))
      const resetRecording = React.useCallback(() => {
        recorderMock.reset()
        setState({ durationSeconds: 0, error: null, isRecording: false, level: 0 })
      }, [])
      const startRecording = React.useCallback(async () => {
        recorderMock.start()
        setState({ durationSeconds: 0, error: null, isRecording: true, level: 0 })
        return true
      }, [])
      const stopRecording = React.useCallback(async () => {
        recorderMock.stop()
        const error = recorderMock.nextStopBlob ? null : '未检测到麦克风输入，请检查系统麦克风和浏览器权限'
        setState({ durationSeconds: 1, error, isRecording: false, level: 0 })
        return recorderMock.nextStopBlob
      }, [])
      return {
        audioBlob: null,
        audioUrl: null,
        ...state,
        resetRecording,
        startRecording,
        stopRecording,
      }
    },
  }
})

vi.mock('../../composables/ai-chat/page/useSpeechWaveform', () => ({
  useSpeechWaveform: () => waveformMock,
}))

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
    evaluateFollowReadPronunciationMock.mockReset()
    explainFollowReadPronunciationMock.mockReset()
    fetchMock.mockReset()
    audioSessionMock.lastOnEnd = null
    audioSessionMock.listeners.clear()
    audioSessionMock.play.mockReset()
    audioSessionMock.prepare.mockReset()
    audioSessionMock.stop.mockReset()
    recorderMock.nextStopBlob = new Blob(['voice'], { type: 'audio/wav' })
    recorderMock.reset.mockReset()
    recorderMock.start.mockReset()
    recorderMock.stop.mockReset()
    waveformMock.attachCanvas.mockReset()
    waveformMock.pushAmplitude.mockReset()
    waveformMock.resetWaveform.mockReset()
    waveformMock.setWaveformRecordingState.mockReset()
    Object.defineProperty(globalThis, 'fetch', {
      value: fetchMock.mockResolvedValue({ ok: true, blob: vi.fn().mockResolvedValue(new Blob(['ref'])) }),
      writable: true,
    })
    Object.defineProperty(window, 'requestAnimationFrame', { value: vi.fn(() => 1), writable: true })
    Object.defineProperty(window, 'cancelAnimationFrame', { value: vi.fn(), writable: true })
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
        bookId="ielts"
        chapterId="1"
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

  it('records manually and shows lightweight segmented feedback', async () => {
    fetchFollowReadWordMock.mockResolvedValue({
      word: 'phenomenon',
      phonetic: '/fəˈnɒmɪnən/',
      definition: '现象',
      pos: 'n.',
      audio_url: '/api/tts/word-audio?w=phenomenon',
      audio_profile: 'full_chunk_full',
      audio_playback_rate: 1,
      chunk_audio_url: '/api/tts/follow-read-chunked-audio?w=phenomenon',
      chunk_audio_profile: 'full_chunk_full_merged',
      estimated_duration_ms: 4200,
      audio_sequence: [
        { id: 'follow-read-track', kind: 'follow', label: '完整示范 -> 拆分跟读 -> 完整回放', url: '/api/tts/follow-read-chunked-audio?w=phenomenon', playback_rate: 1, track_segments: true },
      ],
      segments: [
        { id: 'seg-0', letter_start: 0, letter_end: 3, letters: 'phe', phonetic: 'fə', start_ms: 950, end_ms: 1200 },
        { id: 'seg-1', letter_start: 3, letter_end: 5, letters: 'no', phonetic: 'nə', start_ms: 1300, end_ms: 1600 },
        { id: 'seg-2', letter_start: 5, letter_end: 10, letters: 'menon', phonetic: 'mɪnən', start_ms: 1700, end_ms: 2400 },
      ],
    })
    evaluateFollowReadPronunciationMock.mockResolvedValue({
      word: 'phenomenon',
      score: 76,
      band: 'near_pass',
      passed: false,
      transcript: 'phenomenon',
      feedback: {
        summary: '中段有断裂，先慢读 no 再连回完整单词。',
        stress: '重音基本正确。',
        vowel: '中段元音偏短。',
        consonant: '辅音清晰。',
        ending: '尾音需要收完整。',
        rhythm: '节奏稳定。',
      },
      segmentFeedback: [
        { text: 'fə', score: 90, status: 'good', comment: 'phe 起音清楚。' },
        { text: '/nə/', score: 55, status: 'weak', comment: 'There was a break.' },
        { text: 'mɪnən', score: 74, status: 'ok', comment: 'menon 基本接近。' },
      ],
      weakSegments: ['no'],
      provider: 'dashscope',
      model: 'qwen-audio-turbo',
    })

    const user = userEvent.setup()
    const { container } = render(
      <FollowMode
        currentWord={makeWord()}
        bookId="ielts"
        chapterId="1"
        queueIndex={0}
        total={1}
        settings={{}}
        speechConnected={false}
        speechRecording={false}
        recognizedText=""
        onIndexChange={vi.fn()}
        onCompleteSession={vi.fn(() => Promise.resolve())}
        onStartRecording={vi.fn(() => Promise.resolve())}
        onStopRecording={vi.fn()}
        onSessionInteraction={vi.fn(() => Promise.resolve())}
      />,
    )

    await screen.findByText('/fə/')
    await user.click(screen.getByRole('button', { name: '播放' }))
    expect(audioSessionMock.lastOnEnd).toBeNull()
    expect(recorderMock.start).not.toHaveBeenCalled()
    await user.click(screen.getByRole('button', { name: '播放' }))
    await user.click(screen.getByRole('button', { name: '录音' }))
    await user.click(await screen.findByRole('button', { name: '停止' }))

    await waitFor(() => {
      expect(evaluateFollowReadPronunciationMock).toHaveBeenCalled()
      expect(screen.getByText('76')).toBeInTheDocument()
      expect(screen.getByText('接近通过')).toBeInTheDocument()
    })
    expect(screen.queryByText('基础评分')).not.toBeInTheDocument()
    expect(screen.queryByText('重音')).not.toBeInTheDocument()
    expect(screen.getByText('中段有断裂，先慢读 no 再连回完整单词。')).toBeInTheDocument()
    expect(container.querySelector('.follow-word-part.is-good')?.textContent).toBe('phe')
    expect(container.querySelector('.follow-word-part.is-weak')?.textContent).toBe('no')
    expect(container.querySelector('.follow-word-part.is-ok')?.textContent).toBe('menon')
    expect(container.querySelector('.follow-segment-feedback')).toBeNull()
    expect(evaluateFollowReadPronunciationMock.mock.calls[0][0].segments).toEqual([
      { text: 'phe', phonetic: 'fə' },
      { text: 'no', phonetic: 'nə' },
      { text: 'menon', phonetic: 'mɪnən' },
    ])
  })

  it('rejects scoring responses without complete segment feedback', async () => {
    fetchFollowReadWordMock.mockResolvedValue({
      word: 'phenomenon',
      phonetic: '/fəˈnɒmɪnən/',
      definition: '现象',
      pos: 'n.',
      audio_url: '/api/tts/word-audio?w=phenomenon',
      audio_profile: 'full_chunk_full',
      audio_playback_rate: 1,
      chunk_audio_url: '/api/tts/follow-read-chunked-audio?w=phenomenon',
      chunk_audio_profile: 'full_chunk_full_merged',
      estimated_duration_ms: 4200,
      audio_sequence: [
        { id: 'follow-read-track', kind: 'follow', label: '完整示范 -> 拆分跟读 -> 完整回放', url: '/api/tts/follow-read-chunked-audio?w=phenomenon', playback_rate: 1, track_segments: true },
      ],
      segments: [
        { id: 'seg-0', letter_start: 0, letter_end: 3, letters: 'phe', phonetic: 'fə', start_ms: 950, end_ms: 1200 },
        { id: 'seg-1', letter_start: 3, letter_end: 5, letters: 'no', phonetic: 'nə', start_ms: 1300, end_ms: 1600 },
      ],
    })
    evaluateFollowReadPronunciationMock.mockResolvedValue({
      word: 'phenomenon',
      score: 76,
      band: 'near_pass',
      passed: false,
      transcript: 'phenomenon',
      feedback: {
        summary: '需要重读中段。',
        stress: '重音需要更稳定。',
        vowel: '元音需要更饱满。',
        consonant: '辅音需要更清晰。',
        ending: '收音要完整。',
        rhythm: '节奏需要放慢。',
      },
      weakSegments: ['no'],
      provider: 'dashscope',
      model: 'qwen-audio-turbo',
    })

    const user = userEvent.setup()
    const { container } = render(
      <FollowMode
        currentWord={makeWord()}
        bookId="ielts"
        chapterId="1"
        queueIndex={0}
        total={1}
        settings={{}}
        speechConnected={false}
        speechRecording={false}
        recognizedText=""
        onIndexChange={vi.fn()}
        onCompleteSession={vi.fn(() => Promise.resolve())}
        onStartRecording={vi.fn(() => Promise.resolve())}
        onStopRecording={vi.fn()}
        onSessionInteraction={vi.fn(() => Promise.resolve())}
      />,
    )

    await screen.findByText('/fə/')
    await user.click(screen.getByRole('button', { name: '录音' }))
    await user.click(await screen.findByRole('button', { name: '停止' }))

    await screen.findByText('逐音标评分缺失，请重新跟读')
    expect(screen.queryByText('接近通过')).not.toBeInTheDocument()
    expect(screen.queryByText('76')).not.toBeInTheDocument()
    expect(container.querySelector('.follow-word-part.is-ok')).toBeNull()
    expect(container.querySelector('.follow-word-part.is-weak')).toBeNull()
  })

  it('does not call scoring for empty recording', async () => {
    fetchFollowReadWordMock.mockResolvedValue({
      word: 'phenomenon',
      phonetic: '/fəˈnɒmɪnən/',
      definition: '现象',
      pos: 'n.',
      audio_url: '/api/tts/word-audio?w=phenomenon',
      audio_profile: 'full_chunk_full',
      audio_playback_rate: 1,
      chunk_audio_url: '/api/tts/follow-read-chunked-audio?w=phenomenon',
      chunk_audio_profile: 'full_chunk_full_merged',
      estimated_duration_ms: 4200,
      audio_sequence: [
        { id: 'follow-read-track', kind: 'follow', label: '完整示范 -> 拆分跟读 -> 完整回放', url: '/api/tts/follow-read-chunked-audio?w=phenomenon', playback_rate: 1, track_segments: true },
      ],
      segments: [{ id: 'seg-0', letter_start: 0, letter_end: 10, letters: 'phenomenon', phonetic: 'fəˈnɒmɪnən', start_ms: 950, end_ms: 2400 }],
    })
    recorderMock.nextStopBlob = null

    const user = userEvent.setup()
    render(
      <FollowMode
        currentWord={makeWord()}
        queueIndex={0}
        total={1}
        settings={{}}
        speechConnected={false}
        speechRecording={false}
        recognizedText=""
        onIndexChange={vi.fn()}
        onCompleteSession={vi.fn(() => Promise.resolve())}
        onStartRecording={vi.fn(() => Promise.resolve())}
        onStopRecording={vi.fn()}
        onSessionInteraction={vi.fn(() => Promise.resolve())}
      />,
    )

    await screen.findByText('/fəˈnɒmɪnən/')
    await user.click(screen.getByRole('button', { name: '录音' }))
    await user.click(await screen.findByRole('button', { name: '停止' }))

    await screen.findByText('没有检测到有效跟读，请重试')
    expect(evaluateFollowReadPronunciationMock).not.toHaveBeenCalled()
  })

  it('does not report a pronunciation result when scoring fails', async () => {
    fetchFollowReadWordMock.mockResolvedValue({
      word: 'phenomenon',
      phonetic: '/fəˈnɒmɪnən/',
      definition: '现象',
      pos: 'n.',
      audio_url: '/api/tts/word-audio?w=phenomenon',
      audio_profile: 'full_chunk_full',
      audio_playback_rate: 1,
      chunk_audio_url: '/api/tts/follow-read-chunked-audio?w=phenomenon',
      chunk_audio_profile: 'full_chunk_full_merged',
      estimated_duration_ms: 4200,
      audio_sequence: [
        { id: 'follow-read-track', kind: 'follow', label: '完整示范 -> 拆分跟读 -> 完整回放', url: '/api/tts/follow-read-chunked-audio?w=phenomenon', playback_rate: 1, track_segments: true },
      ],
      segments: [{ id: 'seg-0', letter_start: 0, letter_end: 10, letters: 'phenomenon', phonetic: 'fəˈnɒmɪnən', start_ms: 950, end_ms: 2400 }],
    })
    evaluateFollowReadPronunciationMock.mockRejectedValue(new Error('AI 评分服务额度已用尽，请在 DashScope 控制台处理。'))

    const user = userEvent.setup()
    const onPronunciationEvaluated = vi.fn()
    render(
      <FollowMode
        currentWord={makeWord()}
        bookId="ielts"
        chapterId="1"
        queueIndex={0}
        total={1}
        settings={{}}
        speechConnected={false}
        speechRecording={false}
        recognizedText=""
        onIndexChange={vi.fn()}
        onCompleteSession={vi.fn(() => Promise.resolve())}
        onStartRecording={vi.fn(() => Promise.resolve())}
        onStopRecording={vi.fn()}
        onSessionInteraction={vi.fn(() => Promise.resolve())}
        onPronunciationEvaluated={onPronunciationEvaluated}
      />,
    )

    await screen.findByText('/fəˈnɒmɪnən/')
    await user.click(screen.getByRole('button', { name: '录音' }))
    await user.click(await screen.findByRole('button', { name: '停止' }))

    await waitFor(() => {
      expect(screen.getByText('AI 评分服务额度已用尽，请在 DashScope 控制台处理。')).toBeInTheDocument()
    })
    expect(onPronunciationEvaluated).not.toHaveBeenCalled()
  })
})
