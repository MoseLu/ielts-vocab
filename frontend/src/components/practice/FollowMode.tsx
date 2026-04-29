import { startTransition, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import type { AppSettings, Word } from './types'
import {
  fetchFollowReadWord,
  type FollowReadPayload,
  type FollowReadSegment,
} from './followReadApi'
import {
  getPracticeAudioSnapshot,
  playPracticeAudio,
  preparePracticeAudio,
  stopPracticeAudio,
  subscribePracticeAudio,
} from './practiceAudio.session'
import WordMeaningGroups from '../ui/WordMeaningGroups'
import {
  evaluateFollowReadPronunciation,
  type FollowReadPronunciationResponse,
} from './followReadScoring'

interface FollowModeProps {
  currentWord: Word
  bookId: string | null
  chapterId: string | null
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
  onPronunciationEvaluated?: (word: Word, result: FollowReadPronunciationResponse) => void | Promise<void>
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

export default function FollowMode({
  currentWord,
  bookId,
  chapterId,
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
  onPronunciationEvaluated,
}: FollowModeProps) {
  const [payload, setPayload] = useState<FollowReadPayload | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [localRecording, setLocalRecording] = useState(false)
  const [scoring, setScoring] = useState(false)
  const [scoreResult, setScoreResult] = useState<FollowReadPronunciationResponse | null>(null)
  const [snapshot, setSnapshot] = useState(getPracticeAudioSnapshot())
  const recorderRef = useRef<MediaRecorder | null>(null)
  const recordChunksRef = useRef<Blob[]>([])
  const recordStreamRef = useRef<MediaStream | null>(null)
  const recordStartedAtRef = useRef(0)
  const wordKey = currentWord.word.trim().toLowerCase()

  useEffect(() => subscribePracticeAudio(setSnapshot), [])

  useEffect(() => {
    let cancelled = false
    stopPracticeAudio()
    setLoading(true)
    setError(null)
    setScoreResult(null)
    void fetchFollowReadWord(currentWord)
      .then(nextPayload => {
        if (cancelled) return
        startTransition(() => setPayload(nextPayload))
        void preparePracticeAudio({ kind: 'follow-sequence', payload: nextPayload }).catch(() => {})
      })
      .catch(() => {
        if (!cancelled) setError('跟读素材暂时加载失败')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
      stopPracticeAudio()
    }
  }, [currentWord])

  const isCurrentPlayback = snapshot.origin === 'follow-mode'
    && snapshot.wordKey === wordKey
    && snapshot.queueIndex === queueIndex
  const isPlaying = isCurrentPlayback && snapshot.state === 'playing'
  const durationMs = isCurrentPlayback ? snapshot.durationMs : null
  const currentClipIndex = isCurrentPlayback ? snapshot.clipIndex : -1
  const segments = useMemo(() => (
    payload ? scaleTimeline(payload.segments, payload.estimated_duration_ms, durationMs) : []
  ), [durationMs, payload])
  const activeIndex = useMemo(
    () => getActiveSegmentIndex(segments, isCurrentPlayback ? snapshot.currentTimeMs : 0),
    [isCurrentPlayback, segments, snapshot.currentTimeMs],
  )

  const playAudio = async () => {
    if (!payload) return
    await onSessionInteraction()
    setError(null)
    const started = await playPracticeAudio({
      kind: 'follow-sequence',
      payload,
    }, {
      volume: settings.volume,
    }, {
      origin: 'follow-mode',
      wordKey,
      queueIndex,
    })
    if (!started) setError('跟读音频播放失败')
  }

  const handlePlayClick = () => {
    if (isPlaying) {
      stopPracticeAudio()
      return
    }
    void playAudio().catch(() => setError('跟读音频播放失败'))
  }

  const stopLocalRecording = () => {
    const recorder = recorderRef.current
    if (recorder && recorder.state !== 'inactive') {
      recorder.stop()
      return
    }
    setLocalRecording(false)
  }

  const stopRecordStream = () => {
    recordStreamRef.current?.getTracks().forEach(track => track.stop())
    recordStreamRef.current = null
  }

  const fetchReferenceAudio = async (): Promise<Blob | null> => {
    const url = payload?.chunk_audio_url || payload?.audio_url
    if (!url) return null
    const response = await fetch(url)
    if (!response.ok) return null
    if (typeof response.blob !== 'function') return null
    return response.blob()
  }

  const submitRecordedAudio = async (audio: Blob, durationSeconds: number) => {
    setScoring(true)
    setError(null)
    try {
      const result = await evaluateFollowReadPronunciation({
        word: currentWord.word,
        phonetic: currentWord.phonetic,
        audio,
        referenceAudio: await fetchReferenceAudio(),
        bookId: bookId ?? currentWord.book_id,
        chapterId: chapterId ?? (currentWord.chapter_id != null ? String(currentWord.chapter_id) : null),
        durationSeconds,
      })
      setScoreResult(result)
      await onPronunciationEvaluated?.(currentWord, result)
    } catch {
      setError('跟读评分失败，请重新录一遍')
    } finally {
      setScoring(false)
    }
  }

  const startLocalRecording = async () => {
    const recorderCtor = globalThis.MediaRecorder
    if (!navigator.mediaDevices?.getUserMedia || typeof recorderCtor !== 'function') {
      await onStartRecording()
      return
    }
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    recordStreamRef.current = stream
    recordChunksRef.current = []
    recordStartedAtRef.current = Date.now()
    const recorder = new recorderCtor(stream)
    recorderRef.current = recorder
    recorder.ondataavailable = event => {
      if (event.data.size > 0) recordChunksRef.current.push(event.data)
    }
    recorder.onstop = () => {
      const audio = new Blob(recordChunksRef.current, { type: recordChunksRef.current[0]?.type || 'audio/webm' })
      const durationSeconds = Math.max(1, Math.round((Date.now() - recordStartedAtRef.current) / 1000))
      recorderRef.current = null
      stopRecordStream()
      setLocalRecording(false)
      if (audio.size <= 0) {
        setError('没有录到清晰语音，请重试')
        return
      }
      void submitRecordedAudio(audio, durationSeconds)
    }
    recorder.start()
    setScoreResult(null)
    setLocalRecording(true)
  }

  const handleRecordClick = () => {
    void onSessionInteraction()
    if (localRecording) {
      stopLocalRecording()
      return
    }
    if (speechRecording) {
      onStopRecording()
      return
    }
    void startLocalRecording().catch(() => setError('无法访问麦克风，请检查权限'))
  }

  const handlePrevious = () => {
    if (queueIndex <= 0) return
    stopPracticeAudio()
    onIndexChange(queueIndex - 1)
  }

  const handleNext = () => {
    stopPracticeAudio()
    if (queueIndex + 1 >= total) {
      void onCompleteSession().then(() => onIndexChange(total))
      return
    }
    onIndexChange(queueIndex + 1)
  }

  const playbackLabel = payload?.audio_sequence?.[currentClipIndex]?.label ?? '跟读播放'
  const statusLine = loading
    ? '正在加载跟读时间轴...'
    : error ?? (
        isPlaying
          ? `${playbackLabel} ${Math.max(currentClipIndex + 1, 1)}/${Math.max(payload?.audio_sequence?.length ?? 1, 1)}`
          : '三段式播放：完整示范 -> 拆分跟读 -> 完整回放。'
      )
  const scoreLabel = scoreResult?.band === 'pass'
    ? '通过'
    : scoreResult?.band === 'near_pass'
      ? '接近通过'
      : '需要重读'

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

          <WordMeaningGroups
            className="follow-definition-row"
            definition={currentWord.definition}
            pos={currentWord.pos}
            size="lg"
          />

          <div className="follow-status-line">{statusLine}</div>
          {(speechRecording || recognizedText) && (
            <div className="follow-recording-note">
              {speechRecording ? '录音中...' : `识别结果：${recognizedText || '未识别到内容'}`}
            </div>
          )}
          {localRecording && <div className="follow-recording-note">录音中...</div>}
          {scoring && <div className="follow-recording-note">评分中...</div>}
          {scoreResult && (
            <div className={`follow-recording-note follow-recording-note--${scoreResult.band}`}>
              <strong>{Math.round(scoreResult.score)}</strong>
              <span>{scoreLabel}</span>
              <span>{scoreResult.feedback.summary}</span>
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
          className={`follow-main-btn follow-main-btn--record${localRecording || speechRecording ? ' is-recording' : ''}`}
          onClick={handleRecordClick}
          disabled={scoring || (!speechConnected && typeof globalThis.MediaRecorder !== 'function')}
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
            <rect x="9" y="3" width="6" height="10" rx="3" />
            <path d="M5 11a7 7 0 0 0 14 0" />
            <path d="M12 18v3" />
          </svg>
          {localRecording || speechRecording ? '停止' : scoring ? '评分中' : '录音'}
        </button>
        <button className="follow-nav-btn" onClick={handleNext}>
          {queueIndex + 1 >= total ? '完成' : '下一个'}
        </button>
      </div>
    </div>
  )
}
