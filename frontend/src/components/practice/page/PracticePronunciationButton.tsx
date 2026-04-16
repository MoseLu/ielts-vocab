import { useCallback, useEffect, useId, useRef, useState } from 'react'
import { useSpeechRecognition } from '../../../hooks/useSpeechRecognition'
import {
  AIPronunciationCheckResponseSchema,
  apiFetch,
  safeParse,
  type AIPronunciationCheckResponse,
} from '../../../lib'

const SPEAKING_ICON_PATH =
  'M442 425h140c13.8 0 25-11.2 25-25s-11.2-25-25-25H442c-13.8 0-25 11.2-25 25s11.2 25 25 25zm70 274c111 0 201-90 201-201V260c0-111-90-201-201-201s-201 90-201 201v238c0 111 90 201 201 201zM361 260c0-83.4 67.6-151 151-151s151 67.6 151 151v238c0 83.4-67.6 151-151 151s-151-67.6-151-151V260zm417 163c-12.6-7.1-37 0.3-37 17v94s1.4 57.5-32 106-71.3 76.9-103 93c-31.7 16.1-79.1 22-96 22s-84-11.5-120-39-61.9-57.4-81-90-25-87.5-25-101v-78s-1-16.7-17-23-33.5 9.1-34 21v82s2.7 66.9 30 119c27.3 52.1 71.5 92.4 95 108 21.3 14.1 56.9 41.5 128 48.5V915H372c-13.8 0-25 11.2-25 25s11.2 25 25 25h280c13.8 0 25-11.2 25-25s-11.2-25-25-25H536V803.5c71.7-5 115.1-38.6 137-53.5 24.4-16.5 59.8-46.9 86-99 26.2-52.1 32-73.9 32-118v-90s-0.4-12.9-13-20z'

function normalizeTranscript(value: string) {
  return value
    .toLowerCase()
    .replace(/[^a-z\s'-]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

interface PracticePronunciationButtonProps {
  bookId: string | null
  chapterId: string | null
  targetWord: string
  targetPhonetic?: string | null
  onEvaluated?: (result: AIPronunciationCheckResponse) => void
}

export function PracticePronunciationButton({
  bookId,
  chapterId,
  targetWord,
  targetPhonetic,
  onEvaluated,
}: PracticePronunciationButtonProps) {
  const panelId = useId()
  const wrapperRef = useRef<HTMLDivElement | null>(null)
  const requestIdRef = useRef(0)
  const [isOpen, setIsOpen] = useState(false)
  const [transcript, setTranscript] = useState('')
  const [result, setResult] = useState<AIPronunciationCheckResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isChecking, setIsChecking] = useState(false)

  const resetState = useCallback(() => {
    requestIdRef.current += 1
    setTranscript('')
    setResult(null)
    setError(null)
    setIsChecking(false)
  }, [])

  const closePanel = useCallback(() => {
    resetState()
    setIsOpen(false)
  }, [resetState])

  const submitPronunciation = useCallback(async (spokenText: string) => {
    const normalizedTranscript = normalizeTranscript(spokenText)
    if (!normalizedTranscript) {
      setError(`没有识别到清晰的英文发音，请重新读一遍 ${targetWord}。`)
      return
    }

    const requestId = requestIdRef.current + 1
    requestIdRef.current = requestId
    setTranscript(normalizedTranscript)
    setError(null)
    setResult(null)
    setIsChecking(true)

    try {
      const raw = await apiFetch('/api/ai/pronunciation-check', {
        method: 'POST',
        body: JSON.stringify({
          word: targetWord,
          transcript: normalizedTranscript,
          bookId,
          chapterId,
        }),
      })
      const parsed = safeParse(AIPronunciationCheckResponseSchema, raw)
      if (!parsed.success) {
        throw new Error('发音评分响应格式错误')
      }
      if (requestIdRef.current !== requestId) return
      setResult(parsed.data)
      onEvaluated?.(parsed.data)
    } catch (submissionError) {
      if (requestIdRef.current !== requestId) return
      setError(submissionError instanceof Error ? submissionError.message : '发音评分失败，请稍后重试')
    } finally {
      if (requestIdRef.current === requestId) {
        setIsChecking(false)
      }
    }
  }, [bookId, chapterId, onEvaluated, targetWord])

  const {
    isConnected: speechConnected,
    isRecording: speechRecording,
    isProcessing: speechProcessing,
    startRecording,
    stopRecording,
  } = useSpeechRecognition({
    enabled: isOpen,
    language: 'en',
    enableVad: true,
    autoStop: true,
    onPartial: text => {
      setTranscript(normalizeTranscript(text))
      setError(null)
    },
    onResult: text => {
      const normalizedTranscript = normalizeTranscript(text)
      setTranscript(normalizedTranscript)
      void submitPronunciation(normalizedTranscript)
    },
    onError: message => {
      setError(message)
    },
  })

  const handlePanelToggle = useCallback(() => {
    if (isOpen) {
      closePanel()
      return
    }
    resetState()
    setIsOpen(true)
  }, [closePanel, isOpen, resetState])

  const handleVoiceToggle = useCallback(async () => {
    if (isChecking || speechProcessing) return
    if (speechRecording) {
      stopRecording()
      return
    }
    resetState()
    setIsOpen(true)
    await startRecording()
  }, [isChecking, resetState, speechProcessing, speechRecording, startRecording, stopRecording])

  useEffect(() => {
    if (!isOpen) return

    const handlePointerDown = (event: PointerEvent) => {
      const target = event.target as Node | null
      if (!target || wrapperRef.current?.contains(target)) return
      closePanel()
    }
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        closePanel()
      }
    }

    document.addEventListener('pointerdown', handlePointerDown)
    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('pointerdown', handlePointerDown)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [closePanel, isOpen])

  useEffect(() => {
    resetState()
    setIsOpen(false)
  }, [resetState, targetWord])

  const actionLabel = isChecking
    ? '评分中...'
    : speechProcessing
      ? '识别中...'
      : speechRecording
        ? '结束跟读'
        : result
          ? '再读一次'
          : '开始跟读'
  const statusTone = error
    ? 'error'
    : result
      ? (result.passed ? 'success' : 'warning')
      : (speechRecording ? 'recording' : 'idle')
  const statusText = error
    ? error
    : result
      ? (result.passed ? `匹配成功，${targetWord} 发音通过。` : `还没完全匹配 ${targetWord}，再读清晰一点。`)
      : speechRecording
        ? `正在听你读 ${targetWord}...`
        : '只检查当前单词发音，不会跳转到雅思口语页。'

  return (
    <div
      ref={wrapperRef}
      className={`practice-pronunciation${isOpen ? ' is-open' : ''}`}
    >
      <button
        type="button"
        className="practice-speaking-entry-btn"
        aria-label="单词发音练习"
        aria-controls={isOpen ? panelId : undefined}
        aria-expanded={isOpen}
        aria-haspopup="dialog"
        title="单词发音练习"
        onClick={handlePanelToggle}
      >
        <svg viewBox="0 0 1024 1024" aria-hidden="true">
          <path d={SPEAKING_ICON_PATH} fill="currentColor" />
        </svg>
      </button>

      {isOpen ? (
        <div
          id={panelId}
          className="practice-pronunciation-panel"
          role="dialog"
          aria-modal="false"
          aria-label={`当前单词 ${targetWord} 的发音练习`}
        >
          <button
            type="button"
            className="practice-pronunciation-panel__close"
            aria-label="关闭发音练习"
            onClick={closePanel}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
              <path d="M6 6l12 12M18 6 6 18" />
            </svg>
          </button>

          <div className="practice-pronunciation-panel__eyebrow">单词口语练习</div>
          <div className="practice-pronunciation-panel__word-row">
            <strong className="practice-pronunciation-panel__word">{targetWord}</strong>
            {targetPhonetic ? (
              <span className="practice-pronunciation-panel__phonetic">{targetPhonetic}</span>
            ) : null}
          </div>

          <p className={`practice-pronunciation-panel__status practice-pronunciation-panel__status--${statusTone}`}>
            {statusText}
          </p>

          <div className="practice-pronunciation-panel__transcript">
            <span className="practice-pronunciation-panel__transcript-label">识别结果</span>
            <span className="practice-pronunciation-panel__transcript-value">
              {transcript || '等待你的发音'}
            </span>
          </div>

          {result ? (
            <div className={`practice-pronunciation-panel__result${result.passed ? ' is-passed' : ' is-warning'}`}>
              <div className="practice-pronunciation-panel__result-header">
                <span className="practice-pronunciation-panel__score">{Math.round(result.score)}</span>
                <span className="practice-pronunciation-panel__result-label">
                  {result.passed ? '发音匹配' : '继续强化'}
                </span>
              </div>
              <ul className="practice-pronunciation-panel__feedback-list">
                <li>{result.stress_feedback}</li>
                <li>{result.vowel_feedback}</li>
                <li>{result.speed_feedback}</li>
              </ul>
            </div>
          ) : null}

          <button
            type="button"
            className={`practice-pronunciation-panel__action${speechRecording ? ' is-recording' : ''}`}
            onClick={() => void handleVoiceToggle()}
            disabled={(!speechConnected && !speechRecording) || isChecking || speechProcessing}
          >
            {actionLabel}
          </button>

          {!speechConnected && !speechRecording ? (
            <div className="practice-pronunciation-panel__hint">语音服务未连接，暂时不能做单词口语检测。</div>
          ) : null}
        </div>
      ) : null}
    </div>
  )
}

export default PracticePronunciationButton
