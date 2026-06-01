import { startTransition, useCallback, useEffect, useMemo, useRef, useState, type CSSProperties, type ReactNode } from 'react'
import { apiRequest } from '../../lib'
import type { AppSettings, Word } from './types'
import {
  fetchFollowReadWord,
  type FollowReadPayload,
  type FollowReadSegment,
} from '../../features/practice/audio/followReadApi'
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
  explainFollowReadPronunciation,
  type FollowReadPronunciationResponse,
} from './followReadScoring'
import FollowReadScoreDetails from './FollowReadScoreDetails'
import useSpeakingRecorder from '../../features/speech/hooks/useSpeakingRecorder'
import { useSpeechWaveform } from '../../composables/ai-chat/page/useSpeechWaveform'

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

function containsChinese(value: string) {
  return /[\u4e00-\u9fff]/.test(value)
}

function chineseText(value: string | undefined, fallback: string) {
  const text = String(value || '').trim()
  return text && containsChinese(text) ? text : fallback
}

function normalizeSegmentKey(value: string) {
  return value
    .trim()
    .toLowerCase()
    .replace(/[\/\[\]\sˈˌ]/g, '')
}

function segmentKeys(segment: FollowReadSegment) {
  return [
    segment.letters,
    segment.phonetic,
    segment.audio_phonetic || '',
  ].map(normalizeSegmentKey).filter(Boolean)
}

function buildSegmentStatusMap(
  result: FollowReadPronunciationResponse | null,
  segments: FollowReadSegment[],
) {
  const statusMap = new Map<string, string>()
  if (!result) return statusMap
  const letterKeys = segments.map(segment => normalizeSegmentKey(segment.letters))
  const keyToLetterKey = new Map<string, string>()
  segments.forEach((segment, index) => {
    segmentKeys(segment).forEach(key => keyToLetterKey.set(key, letterKeys[index]))
  })
  const feedback = result.segmentFeedback || []
  feedback.forEach((segment, index) => {
    const key = normalizeSegmentKey(segment.text)
    const exactKey = keyToLetterKey.get(key)
    if (exactKey) {
      statusMap.set(exactKey, segment.status)
      return
    }
    if (feedback.length === segments.length && letterKeys[index]) {
      statusMap.set(letterKeys[index], segment.status)
    }
  })
  result.weakSegments?.forEach(segment => {
    const key = keyToLetterKey.get(normalizeSegmentKey(segment))
    if (key) statusMap.set(key, 'weak')
  })
  return statusMap
}

function hasCompleteSegmentFeedback(
  result: FollowReadPronunciationResponse,
  segments: FollowReadSegment[],
) {
  if (!segments.length) return true
  if (!result.segmentFeedback?.length) return false
  return buildSegmentStatusMap(result, segments).size >= segments.length
}

function segmentStatusClass(segment: FollowReadSegment, statusMap: Map<string, string>) {
  const status = statusMap.get(normalizeSegmentKey(segment.letters))
  return status === 'good' || status === 'ok' || status === 'weak'
    ? ` is-${status}`
    : ''
}

function renderWordSegments(
  word: string,
  segments: FollowReadSegment[],
  activeIndex: number,
  statusMap: Map<string, string>,
) {
  const nodes: React.ReactNode[] = []
  let cursor = 0
  segments.forEach((segment, index) => {
    if (segment.letter_start > cursor) {
      nodes.push(<span key={`gap-${index}`}>{word.slice(cursor, segment.letter_start)}</span>)
    }
    nodes.push(
      <span
        key={segment.id}
        className={`follow-word-part${index === activeIndex ? ' is-active' : ''}${index < activeIndex ? ' is-past' : ''}${segmentStatusClass(segment, statusMap)}`}
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
  favoriteSlot,
  onIndexChange,
  onCompleteSession,
  onSessionInteraction,
  onPronunciationEvaluated,
}: FollowModeProps) {
  const [payload, setPayload] = useState<FollowReadPayload | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [scoring, setScoring] = useState(false)
  const [scoreResult, setScoreResult] = useState<FollowReadPronunciationResponse | null>(null)
  const [scoreSummaryOverride, setScoreSummaryOverride] = useState('')
  const [snapshot, setSnapshot] = useState(getPracticeAudioSnapshot())
  const recorder = useSpeakingRecorder()
  const {
    attachCanvas,
    pushAmplitude,
    resetWaveform,
    setWaveformRecordingState,
  } = useSpeechWaveform()
  const recordingStartedAtRef = useRef(0)
  const stoppingRecordingRef = useRef(false)
  const explanationRequestRef = useRef(0)
  const wordKey = currentWord.word.trim().toLowerCase()

  useEffect(() => subscribePracticeAudio(setSnapshot), [])

  useEffect(() => {
    let cancelled = false
    stopPracticeAudio()
    recorder.resetRecording()
    resetWaveform()
    setLoading(true)
    setError(null)
    setScoreResult(null)
    setScoreSummaryOverride('')
    explanationRequestRef.current += 1
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
  }, [currentWord, recorder.resetRecording, resetWaveform])

  const isCurrentPlayback = snapshot.origin === 'follow-mode'
    && snapshot.wordKey === wordKey
    && snapshot.queueIndex === queueIndex
  const isPlaying = isCurrentPlayback && snapshot.state === 'playing'
  const durationMs = isCurrentPlayback ? snapshot.durationMs : null
  const segments = useMemo(() => (
    payload ? scaleTimeline(payload.segments, payload.estimated_duration_ms, durationMs) : []
  ), [durationMs, payload])
  const segmentStatusMap = useMemo(
    () => buildSegmentStatusMap(scoreResult, segments),
    [scoreResult, segments],
  )
  const activeIndex = useMemo(
    () => getActiveSegmentIndex(segments, isCurrentPlayback ? snapshot.currentTimeMs : 0),
    [isCurrentPlayback, segments, snapshot.currentTimeMs],
  )
  const progressPercent = total > 0
    ? (Math.min(queueIndex + 1, total) / total) * 100
    : 0

  const fetchReferenceAudio = useCallback(async (): Promise<Blob | null> => {
    const url = payload?.chunk_audio_url || payload?.audio_url
    if (!url) return null
    const response = await apiRequest(url)
    if (!response.ok) return null
    if (typeof response.blob !== 'function') return null
    return response.blob()
  }, [payload?.audio_url, payload?.chunk_audio_url])

  const submitRecordedAudio = useCallback(async (audio: Blob, durationSeconds: number) => {
    setScoring(true)
    setError(null)
    try {
      const submittedSegments = payload?.segments || []
      const result = await evaluateFollowReadPronunciation({
        word: currentWord.word,
        phonetic: currentWord.phonetic,
        audio,
        referenceAudio: await fetchReferenceAudio(),
        bookId: bookId ?? currentWord.book_id,
        chapterId: chapterId ?? (currentWord.chapter_id != null ? String(currentWord.chapter_id) : null),
        durationSeconds,
        segments: submittedSegments.map(segment => ({
          text: segment.letters,
          phonetic: segment.audio_phonetic || segment.phonetic,
        })),
      })
      if (!hasCompleteSegmentFeedback(result, submittedSegments)) {
        setError('逐音标评分缺失，请重新跟读')
        return
      }
      setScoreResult(result)
      setScoreSummaryOverride('')
      const explanationRequest = ++explanationRequestRef.current
      if (result.explanationToken) {
        void explainFollowReadPronunciation(result.explanationToken)
          .then(summary => {
            if (summary && explanationRequestRef.current === explanationRequest) {
              setScoreSummaryOverride(summary)
            }
          })
          .catch(() => {})
      }
      await onPronunciationEvaluated?.(currentWord, result)
    } catch (err) {
      const message = err instanceof Error && err.message.trim()
        ? err.message.trim()
        : '跟读评分失败，请稍后重试'
      setError(message)
    } finally {
      setScoring(false)
    }
  }, [
    bookId,
    chapterId,
    currentWord,
    fetchReferenceAudio,
    onPronunciationEvaluated,
    payload?.segments,
  ])

  const stopCurrentRecording = useCallback(async () => {
    if (stoppingRecordingRef.current || !recorder.isRecording) return
    stoppingRecordingRef.current = true
    const durationSeconds = Math.max(1, Math.round((performance.now() - recordingStartedAtRef.current) / 1000))
    const audio = await recorder.stopRecording().finally(() => {
      stoppingRecordingRef.current = false
    })
    if (!audio) {
      setError('没有检测到有效跟读，请重试')
      return
    }
    await submitRecordedAudio(audio, durationSeconds)
  }, [recorder.isRecording, recorder.stopRecording, submitRecordedAudio])

  const startManualRecording = useCallback(async () => {
    if (recorder.isRecording || scoring) return
    recordingStartedAtRef.current = performance.now()
    stoppingRecordingRef.current = false
    resetWaveform()
    setWaveformRecordingState(true)
    setScoreResult(null)
    setError(null)
    const started = await recorder.startRecording()
    if (!started) {
      setWaveformRecordingState(false)
      resetWaveform()
    }
  }, [recorder.isRecording, recorder.startRecording, resetWaveform, scoring, setWaveformRecordingState])

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

  const handleRecordClick = () => {
    void onSessionInteraction()
    if (recorder.isRecording) {
      void stopCurrentRecording()
      return
    }
    void startManualRecording()
  }

  useEffect(() => {
    setWaveformRecordingState(recorder.isRecording)
    if (!recorder.isRecording) return
    pushAmplitude(recorder.level)
  }, [pushAmplitude, recorder.isRecording, recorder.level, setWaveformRecordingState])

  useEffect(() => {
    if (recorder.error) setError(recorder.error)
  }, [recorder.error])

  const handlePrevious = () => {
    if (queueIndex <= 0) return
    recorder.resetRecording()
    stopPracticeAudio()
    onIndexChange(queueIndex - 1)
  }

  const handleNext = () => {
    recorder.resetRecording()
    stopPracticeAudio()
    if (queueIndex + 1 >= total) {
      void onCompleteSession().then(() => onIndexChange(total))
      return
    }
    onIndexChange(queueIndex + 1)
  }

  const statusLine = loading
    ? '正在加载跟读素材...'
    : error
  const scoreLabel = scoreResult?.band === 'pass'
    ? '通过'
    : scoreResult?.band === 'near_pass'
      ? '接近通过'
      : '需要重读'
  const scoreSummary = scoreResult
    ? chineseText(scoreSummaryOverride || scoreResult.feedback.summary, '已完成跟读评分，请根据上方标色分段重读需要加强的位置。')
    : ''

  return (
    <div className="follow-mode">
      <section className="follow-stage" aria-label="跟读练习">
        <div className="follow-progress-track" aria-hidden="true">
          <div
            className="follow-progress-fill"
            style={{ '--progress-percent': `${progressPercent}%` } as CSSProperties}
          />
        </div>
        <div className="follow-progress-label">{Math.min(queueIndex + 1, total)} / {total}</div>

        <div className="follow-media-slot" aria-hidden="true">
          <div className="follow-media-orb">
            <span>Follow</span>
            <small>full / split / full</small>
          </div>
        </div>

        <div className="follow-focus-panel">
          {favoriteSlot && <div className="follow-favorite-slot">{favoriteSlot}</div>}

          <div className="follow-word-row" aria-label={currentWord.word}>
            {segments.length ? renderWordSegments(currentWord.word, segments, activeIndex, segmentStatusMap) : currentWord.word}
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

          {statusLine && <div className="follow-status-line">{statusLine}</div>}
          {recorder.isRecording && (
            <div className="follow-waveform" role="img" aria-label="正在录音">
              <canvas ref={attachCanvas} />
            </div>
          )}
          {scoring && <div className="follow-recording-note">评分中...</div>}
          {scoreResult && (
            <FollowReadScoreDetails result={scoreResult} label={scoreLabel} summary={scoreSummary} />
          )}

          <div className="follow-controls" aria-label="跟读控制">
            <button className="follow-nav-btn" onClick={handlePrevious} disabled={queueIndex <= 0}>
              上一个
            </button>
            <button className={`follow-main-btn${isPlaying ? ' is-playing' : ''}`} onClick={handlePlayClick} disabled={!payload || loading || recorder.isRecording || scoring}>
              <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                {isPlaying ? <rect x="7" y="5" width="4" height="14" rx="1" /> : <path d="M8 5v14l11-7z" />}
                {isPlaying ? <rect x="13" y="5" width="4" height="14" rx="1" /> : null}
              </svg>
              播放
            </button>
            <button
              className={`follow-main-btn follow-main-btn--record${recorder.isRecording ? ' is-recording' : ''}`}
              onClick={handleRecordClick}
              disabled={scoring || isPlaying}
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                <rect x="9" y="3" width="6" height="10" rx="3" />
                <path d="M5 11a7 7 0 0 0 14 0" />
                <path d="M12 18v3" />
              </svg>
              {recorder.isRecording ? '停止' : scoring ? '评分中' : '录音'}
            </button>
            <button className="follow-nav-btn" onClick={handleNext}>
              {queueIndex + 1 >= total ? '完成' : '下一个'}
            </button>
          </div>
        </div>
      </section>
    </div>
  )
}
