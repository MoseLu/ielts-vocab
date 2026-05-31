import { useCallback, useState } from 'react'
import { useSpeechRecognition } from '../../../../hooks/useSpeechRecognition'
import { normalizeAnswer } from '../../../../features/practice/gameMode/gameData'
import { gameAsset } from './gameAssets'

export function SpeakingRecorder({
  targetWord,
  prompt,
  disabled,
  onEvaluated,
}: {
  targetWord: string
  prompt: string
  disabled: boolean
  onEvaluated: (passed: boolean, transcript: string) => void
}) {
  const [transcript, setTranscript] = useState('')
  const [error, setError] = useState<string | null>(null)
  const {
    isConnected,
    isRecording,
    isProcessing,
    startRecording,
    stopRecording,
  } = useSpeechRecognition({
    enabled: true,
    language: 'en',
    enableVad: true,
    autoStop: true,
    onPartial: text => {
      setTranscript(text)
      setError(null)
    },
    onResult: text => {
      const normalizedTranscript = normalizeAnswer(text)
      setTranscript(text)
      onEvaluated(
        normalizedTranscript.includes(normalizeAnswer(targetWord)),
        normalizedTranscript,
      )
    },
    onError: message => setError(message),
  })

  const lowerError = String(error || '').toLowerCase()
  const micIcon = error
    ? (lowerError.includes('permission') || error.includes('权限')
      ? gameAsset.mic.permissionFail
      : gameAsset.mic.disconnected)
    : isProcessing
      ? gameAsset.mic.recognizing
      : isRecording
        ? gameAsset.mic.recording
        : !isConnected
          ? gameAsset.mic.disconnected
          : gameAsset.mic.idle

  const handleToggle = useCallback(async () => {
    if (disabled || isProcessing) return
    if (isRecording) {
      stopRecording()
      return
    }
    setTranscript('')
    setError(null)
    await startRecording()
  }, [disabled, isProcessing, isRecording, startRecording, stopRecording])

  return (
    <div className="practice-game-speaking">
      <div className="practice-game-speaking__status">
        <img src={micIcon} alt="" aria-hidden="true" className="practice-game-speaking__icon" />
        <strong>{isProcessing ? '识别中' : isRecording ? '录音中' : error ? '录音异常' : !isConnected ? '语音未连接' : '准备录音'}</strong>
      </div>
      <p>{prompt}</p>
      <div className="practice-game-speaking__transcript">
        {transcript || '点击录音后，说一句包含目标词的英文短句。'}
      </div>
      {error ? <div className="practice-game-mode__error">{error}</div> : null}
      <button
        type="button"
        className={`practice-game-mode__action${isRecording ? ' is-recording' : ''}`}
        onClick={() => void handleToggle()}
        disabled={disabled || (!isConnected && !isRecording) || isProcessing}
      >
        {isProcessing ? '识别中...' : isRecording ? '结束录音' : '开始录音'}
      </button>
      {!isConnected && !isRecording ? <small>语音服务未连接，暂时不能录音。</small> : null}
    </div>
  )
}
