import { startTransition, useCallback, useEffect, useRef, useState, type ReactNode } from 'react'
import { buildApiUrl } from '../../lib'
import type { AppSettings, Word } from './types'
import {
  fetchFollowReadWord,
  type FollowReadAudioClip,
  type FollowReadPayload,
  type FollowReadSegment,
} from './followReadApi'
import { stopAudio } from './utils'

interface FollowModeProps {
  currentWord: Word
  queueIndex: number
  total: number
  settings: AppSettings
  speechConnected: boolean
  speechRecording: boolean
  recognizedText: string
  favoriteSlot?: ReactNode
  onIndexChange: (index: number) => void
  onCompleteSession: () => Promise<void>
  onStartRecording: () => Promise<void>
  onStopRecording: () => void
  onSessionInteraction: () => Promise<void>
}

function scaleTimeline(segments: FollowReadSegment[], estimatedMs: number, durationMs: number | null) {
  if (!durationMs || durationMs <= 0 || estimatedMs <= 0) return segments
  const scale = durationMs / estimatedMs
  return segments.map(segment => ({
    ...segment,
    start_ms: Math.round(segment.start_ms * scale),
    end_ms: Math.max(1, Math.round(segment.end_ms * scale)),
  }))
}

function getActiveSegmentIndex(segments: FollowReadSegment[], timeMs: number): number {
  const activeIndex = segments.findIndex(segment => timeMs >= segment.start_ms && timeMs < segment.end_ms)
  if (activeIndex >= 0) return activeIndex
  return -1
}

function renderWordSegments(word: string, segments: FollowReadSegment[], activeIndex: number) {
  const nodes: React.ReactNode[] = []
  let cursor = 0
  segments.forEach((segment, index) => {
    if (segment.letter_start > cursor) {
      nodes.push(<span key={`gap-${index}`}>{word.slice(cursor, segment.letter_start)}</span>)
    }
    nodes.push(
      <span
        key={segment.id}
        className={`follow-word-part${index === activeIndex ? ' is-active' : ''}${index < activeIndex ? ' is-past' : ''}`}
      >
        {word.slice(segment.letter_start, segment.letter_end)}
      </span>,
    )
    cursor = segment.letter_end
  })
  if (cursor < word.length) nodes.push(<span key="tail">{word.slice(cursor)}</span>)
  return nodes
}

function resolveAudioSequence(payload: FollowReadPayload): FollowReadAudioClip[] {
  return payload.audio_sequence?.length
    ? payload.audio_sequence
    : [{
        id: 'full-fallback',
        kind: 'full',
        label: '完整示范',
        url: payload.audio_url,
        playback_rate: payload.audio_playback_rate || 1,
        track_segments: true,
      }]
}

export default function FollowMode({
  currentWord,
  queueIndex,
  total,
  settings,
  speechConnected,
  speechRecording,
  recognizedText,
  favoriteSlot,
  onIndexChange,
  onCompleteSession,
  onStartRecording,
  onStopRecording,
  onSessionInteraction,
}: FollowModeProps) {
  const [payload, setPayload] = useState<FollowReadPayload | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [activeIndex, setActiveIndex] = useState(-1)
  const [durationMs, setDurationMs] = useState<number | null>(null)
  const [currentClipIndex, setCurrentClipIndex] = useState(-1)
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const frameRef = useRef<number | null>(null)
  const clipIndexRef = useRef(-1)
  const clipRef = useRef<FollowReadAudioClip | null>(null)
  const sequenceRef = useRef<FollowReadAudioClip[]>([])
  const preparedAudioRef = useRef<Map<string, HTMLAudioElement>>(new Map())

  const segments = payload
    ? scaleTimeline(payload.segments, payload.estimated_duration_ms, durationMs)
    : []

  const releaseCurrentAudio = useCallback(() => {
    if (frameRef.current != null) window.cancelAnimationFrame(frameRef.current)
    frameRef.current = null
    if (audioRef.current) {
      audioRef.current.pause()
      audioRef.current.onended = null
      audioRef.current.onerror = null
      audioRef.current.onloadedmetadata = null
      audioRef.current = null
    }
  }, [])

  const resetPreparedAudio = useCallback(() => {
    preparedAudioRef.current.forEach(audio => {
      audio.pause()
      audio.onended = null
      audio.onerror = null
      audio.onloadedmetadata = null
    })
    preparedAudioRef.current.clear()
  }, [])

  const stopLocalAudio = useCallback((resetSequence = true) => {
    releaseCurrentAudio()
    if (resetSequence) {
      clipIndexRef.current = -1
      clipRef.current = null
      sequenceRef.current = []
      setCurrentClipIndex(-1)
      setActiveIndex(-1)
      setDurationMs(null)
    }
    setIsPlaying(false)
  }, [releaseCurrentAudio])

  useEffect(() => {
    let cancelled = false
    stopLocalAudio()
    resetPreparedAudio()
    setActiveIndex(-1)
    setDurationMs(null)
    setLoading(true)
    setError(null)
    void fetchFollowReadWord(currentWord)
      .then(nextPayload => {
        if (cancelled) return
        startTransition(() => setPayload(nextPayload))
      })
      .catch(() => {
        if (!cancelled) setError('跟读素材暂时加载失败')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
      stopLocalAudio()
      resetPreparedAudio()
    }
  }, [currentWord, resetPreparedAudio, stopLocalAudio])

  useEffect(() => {
    resetPreparedAudio()
    if (!payload) return

    const prepared = new Map<string, HTMLAudioElement>()
    resolveAudioSequence(payload).forEach(clip => {
      const audio = new Audio(buildApiUrl(clip.url))
      audio.preload = 'auto'
      audio.load?.()
      prepared.set(clip.id, audio)
    })
    preparedAudioRef.current = prepared
    return resetPreparedAudio
  }, [payload, resetPreparedAudio])

  const syncActiveSegment = () => {
    const audio = audioRef.current
    if (!audio || !payload || !clipRef.current?.track_segments) return
    const nextIndex = getActiveSegmentIndex(segments, audio.currentTime * 1000)
    setActiveIndex(previous => (previous === nextIndex ? previous : nextIndex))
    if (!audio.paused && !audio.ended) {
      frameRef.current = window.requestAnimationFrame(syncActiveSegment)
    }
  }

  const playClipAt = useCallback(async (index: number) => {
    const clip = sequenceRef.current[index]
    if (!clip) {
      stopLocalAudio()
      return
    }

    releaseCurrentAudio()
    clipIndexRef.current = index
    clipRef.current = clip
    setCurrentClipIndex(index)
    setDurationMs(null)
    if (!clip.track_segments) setActiveIndex(-1)

    const audio = preparedAudioRef.current.get(clip.id) ?? new Audio(buildApiUrl(clip.url))
    audio.preload = 'auto'
    audio.pause()
    audio.currentTime = 0
    const volume = Number(settings.volume ?? '100') / 100
    audio.volume = Number.isFinite(volume) ? Math.min(1, Math.max(0, volume)) : 1
    audio.playbackRate = Math.min(1.15, Math.max(0.72, Number(clip.playback_rate) || 1))
    const syncClipDuration = () => {
      if (clip.track_segments && Number.isFinite(audio.duration) && audio.duration > 0) {
        setDurationMs(Math.round(audio.duration * 1000))
      }
    }
    audio.onloadedmetadata = syncClipDuration
    syncClipDuration()
    audio.onended = () => {
      const nextIndex = index + 1
      if (nextIndex < sequenceRef.current.length) {
        void playClipAt(nextIndex)
        return
      }
      stopLocalAudio()
    }
    audio.onerror = () => {
      stopLocalAudio()
      setError('跟读音频播放失败')
    }
    audioRef.current = audio
    await audio.play()
    setIsPlaying(true)
    if (clip.track_segments) {
      syncActiveSegment()
    }
  }, [releaseCurrentAudio, settings.volume, stopLocalAudio])

  const playAudio = async () => {
    if (!payload) return
    await onSessionInteraction()
    if (audioRef.current && audioRef.current.paused && audioRef.current.currentTime > 0) {
      await audioRef.current.play()
      setIsPlaying(true)
      if (clipRef.current?.track_segments) syncActiveSegment()
      return
    }

    stopAudio()
    stopLocalAudio()
    sequenceRef.current = resolveAudioSequence(payload)
    await playClipAt(0)
  }

  const handlePlayClick = () => {
    if (audioRef.current && !audioRef.current.paused) {
      audioRef.current.pause()
      setIsPlaying(false)
      return
    }
    void playAudio().catch(() => setError('跟读音频播放失败'))
  }

  const handleRecordClick = () => {
    void onSessionInteraction()
    if (speechRecording) {
      onStopRecording()
      return
    }
    void onStartRecording()
  }

  const handlePrevious = () => {
    if (queueIndex <= 0) return
    stopLocalAudio()
    onIndexChange(queueIndex - 1)
  }

  const handleNext = () => {
    stopLocalAudio()
    if (queueIndex + 1 >= total) {
      void onCompleteSession().then(() => onIndexChange(total))
      return
    }
    onIndexChange(queueIndex + 1)
  }

  return (
    <div className="follow-mode">
      <section className="follow-stage" aria-label="跟读练习">
        <div className="follow-media-slot" aria-hidden="true">
          <div className="follow-media-orb">
            <span>Follow</span>
            <small>full / split / full</small>
          </div>
        </div>

        <div className="follow-focus-panel">
          <div className="follow-panel-top">
            <span className="follow-mode-kicker">跟读模式</span>
            <span className="follow-progress">{Math.min(queueIndex + 1, total)} / {total}</span>
            <div className="follow-favorite-slot">{favoriteSlot}</div>
          </div>

          <div className="follow-word-row" aria-label={currentWord.word}>
            {segments.length ? renderWordSegments(currentWord.word, segments, activeIndex) : currentWord.word}
          </div>

          <div className="follow-phonetic-row" aria-label="音标拆分">
            {segments.length ? segments.map((segment, index) => (
              <span
                key={segment.id}
                className={`follow-phonetic-chip${index === activeIndex ? ' is-active' : ''}${index < activeIndex ? ' is-past' : ''}`}
              >
                /{segment.phonetic}/
              </span>
            )) : <span className="follow-phonetic-chip">{currentWord.phonetic}</span>}
          </div>

          <div className="follow-definition-row">
            {currentWord.pos ? <span className="word-pos-tag">{currentWord.pos}</span> : null}
            <span>{currentWord.definition}</span>
          </div>

          <div className="follow-status-line">
            {loading
              ? '正在加载跟读时间轴...'
              : error ?? (
                  isPlaying
                    ? `${payload?.audio_sequence?.[currentClipIndex]?.label ?? '跟读播放'} ${Math.max(currentClipIndex + 1, 1)}/${Math.max(payload?.audio_sequence?.length ?? 1, 1)}`
                    : '三段式播放：完整示范 -> 拆分跟读 -> 完整回放。'
                )}
          </div>
          {(speechRecording || recognizedText) && (
            <div className="follow-recording-note">
              {speechRecording ? '录音中...' : `识别结果：${recognizedText || '未识别到内容'}`}
            </div>
          )}
        </div>
      </section>

      <div className="follow-controls" aria-label="跟读控制">
        <button className="follow-nav-btn" onClick={handlePrevious} disabled={queueIndex <= 0}>
          上一个
        </button>
        <button className={`follow-main-btn${isPlaying ? ' is-playing' : ''}`} onClick={handlePlayClick} disabled={!payload || loading}>
          <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
            {isPlaying ? <rect x="7" y="5" width="4" height="14" rx="1" /> : <path d="M8 5v14l11-7z" />}
            {isPlaying ? <rect x="13" y="5" width="4" height="14" rx="1" /> : null}
          </svg>
          播放
        </button>
        <button
          className={`follow-main-btn follow-main-btn--record${speechRecording ? ' is-recording' : ''}`}
          onClick={handleRecordClick}
          disabled={!speechConnected}
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
            <rect x="9" y="3" width="6" height="10" rx="3" />
            <path d="M5 11a7 7 0 0 0 14 0" />
            <path d="M12 18v3" />
          </svg>
          {speechRecording ? '停止' : '录音'}
        </button>
        <button className="follow-nav-btn" onClick={handleNext}>
          {queueIndex + 1 >= total ? '完成' : '下一个'}
        </button>
      </div>
    </div>
  )
}
