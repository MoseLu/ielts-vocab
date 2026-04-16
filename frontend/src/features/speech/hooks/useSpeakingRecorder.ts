import { useCallback, useEffect, useRef, useState } from 'react'

import { startSpeechAudioCapture, type SpeechAudioCaptureSession } from './speechRecognitionAudioCapture'
import {
  SPEECH_NO_SIGNAL_MESSAGE,
  buildWavBlobFromPcmChunks,
  hasAudiblePcmSignal,
} from './speechRecognitionUtils'

interface SpeakingRecorderState {
  audioBlob: Blob | null
  audioUrl: string | null
  durationSeconds: number
  error: string | null
  isRecording: boolean
  level: number
}

interface SpeakingRecorderActions {
  resetRecording: () => void
  startRecording: () => Promise<void>
  stopRecording: () => Promise<Blob | null>
}

export type SpeakingRecorderResult = SpeakingRecorderState & SpeakingRecorderActions

function stopStreamTracks(stream: MediaStream | null) {
  stream?.getTracks().forEach(track => {
    try {
      track.stop()
    } catch {}
  })
}

function revokeAudioUrl(url: string | null) {
  if (!url) return
  try {
    URL.revokeObjectURL(url)
  } catch {}
}

function mapRecorderError(error: unknown) {
  if (error instanceof DOMException) {
    if (error.name === 'NotAllowedError' || error.name === 'SecurityError') {
      return '未获得麦克风权限，请允许浏览器访问麦克风后重试'
    }
    if (error.name === 'NotFoundError') {
      return '未检测到可用麦克风，请检查设备后重试'
    }
    if (error.name === 'NotReadableError') {
      return '麦克风正被其他程序占用，请关闭后重试'
    }
  }
  if (error instanceof Error && error.message.trim()) {
    return error.message.trim()
  }
  return '录音启动失败，请稍后重试'
}

export function useSpeakingRecorder(): SpeakingRecorderResult {
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null)
  const [audioUrl, setAudioUrl] = useState<string | null>(null)
  const [durationSeconds, setDurationSeconds] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [isRecording, setIsRecording] = useState(false)
  const [level, setLevel] = useState(0)

  const audioUrlRef = useRef<string | null>(null)
  const captureSessionRef = useRef<SpeechAudioCaptureSession | null>(null)
  const durationTimerRef = useRef<number | null>(null)
  const pcmChunksRef = useRef<Int16Array[]>([])
  const startedAtRef = useRef<number | null>(null)
  const streamRef = useRef<MediaStream | null>(null)

  const clearDurationTimer = useCallback(() => {
    if (durationTimerRef.current === null) return
    window.clearInterval(durationTimerRef.current)
    durationTimerRef.current = null
  }, [])

  const releaseResources = useCallback(async () => {
    clearDurationTimer()
    const captureSession = captureSessionRef.current
    captureSessionRef.current = null
    if (captureSession) {
      await captureSession.stop().catch(() => {})
    }
    stopStreamTracks(streamRef.current)
    streamRef.current = null
    startedAtRef.current = null
    setIsRecording(false)
    setLevel(0)
  }, [clearDurationTimer])

  const resetRecording = useCallback(() => {
    void releaseResources()
    pcmChunksRef.current = []
    revokeAudioUrl(audioUrlRef.current)
    audioUrlRef.current = null
    setAudioBlob(null)
    setAudioUrl(null)
    setDurationSeconds(0)
    setError(null)
  }, [releaseResources])

  const startRecording = useCallback(async () => {
    try {
      await releaseResources()
      revokeAudioUrl(audioUrlRef.current)
      audioUrlRef.current = null
      pcmChunksRef.current = []
      setAudioBlob(null)
      setAudioUrl(null)
      setDurationSeconds(0)
      setError(null)
      setLevel(0)

      if (!navigator.mediaDevices?.getUserMedia) {
        throw new Error('当前浏览器不支持麦克风录音')
      }

      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
        },
      })
      streamRef.current = stream
      startedAtRef.current = window.performance.now()
      durationTimerRef.current = window.setInterval(() => {
        const startedAt = startedAtRef.current
        if (startedAt === null) return
        setDurationSeconds(Math.max(0, Math.round((window.performance.now() - startedAt) / 1000)))
      }, 250)
      captureSessionRef.current = await startSpeechAudioCapture({
        stream,
        onLevel: nextLevel => setLevel(nextLevel),
        onPcmFrame: pcmData => {
          if (pcmData.length > 0) {
            pcmChunksRef.current.push(pcmData)
          }
        },
      })
      setIsRecording(true)
    } catch (nextError: unknown) {
      await releaseResources()
      setError(mapRecorderError(nextError))
    }
  }, [releaseResources])

  const stopRecording = useCallback(async () => {
    const startedAt = startedAtRef.current
    await releaseResources()
    if (startedAt !== null) {
      setDurationSeconds(Math.max(0, Math.round((window.performance.now() - startedAt) / 1000)))
    }

    const pcmChunks = pcmChunksRef.current
    if (!pcmChunks.length || !pcmChunks.some(chunk => hasAudiblePcmSignal(chunk))) {
      setError(SPEECH_NO_SIGNAL_MESSAGE)
      return null
    }

    const nextAudioBlob = buildWavBlobFromPcmChunks(pcmChunks)
    const nextAudioUrl = URL.createObjectURL(nextAudioBlob)
    revokeAudioUrl(audioUrlRef.current)
    audioUrlRef.current = nextAudioUrl
    setAudioBlob(nextAudioBlob)
    setAudioUrl(nextAudioUrl)
    setError(null)
    return nextAudioBlob
  }, [releaseResources])

  useEffect(() => () => {
    void releaseResources()
    revokeAudioUrl(audioUrlRef.current)
  }, [releaseResources])

  return {
    audioBlob,
    audioUrl,
    durationSeconds,
    error,
    isRecording,
    level,
    resetRecording,
    startRecording,
    stopRecording,
  }
}

export default useSpeakingRecorder
