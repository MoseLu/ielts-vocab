import { useState, useRef, useCallback, useEffect } from 'react'
import { io, Socket } from 'socket.io-client'
import type {
  CallbacksRef,
  ConnectedPayload,
  FinalResultPayload,
  PartialResultPayload,
  RecognitionErrorPayload,
  RecognitionStartedPayload,
  SpeechRecognitionOptions,
  UseSpeechRecognitionReturn,
} from './speechRecognitionTypes'
import {
  createBrowserSpeechRecognition,
  hasAudiblePcmSignal,
  resolveSpeechSocketConfig,
  SPEECH_EMPTY_RESULT_MESSAGE,
  SPEECH_IDLE_LEVEL,
  SPEECH_MIN_ACTIVE_LEVEL,
  SPEECH_NO_SIGNAL_MESSAGE,
  type BrowserSpeechRecognitionInstance,
} from './speechRecognitionUtils'
import { startSpeechAudioCapture } from './speechRecognitionAudioCapture'
import { requestRecordedAudioFallback as requestRecordedAudioFallbackTask, startMediaRecorderCapture, uploadRecordedAudio as uploadRecordedAudioTask } from './speechRecognitionFileFallback'
import { flushBufferedSocketAudio, queueBufferedSocketAudio, resetBufferedSocketAudio, type BufferedSocketAudioState } from './speechRecognitionSocketAudioBuffer'
export function useSpeechRecognition({
  enabled = true,
  language = 'zh',
  enableVad = true,
  autoStop = true,
  autoStopDelay = 1500,
  enableBrowserRecognition = true,
  enableRealtimeRecognition = true,
  onResult,
  onPartial,
  onError,
  onLevel,
}: SpeechRecognitionOptions): UseSpeechRecognitionReturn {
  const [isConnected, setIsConnected] = useState(false)
  const [isRecording, setIsRecording] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [isReady, setIsReady] = useState(false)
  const socketRef = useRef<Socket | null>(null)
  const audioCaptureStopRef = useRef<(() => Promise<void>) | null>(null)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const browserRecognitionRef = useRef<BrowserSpeechRecognitionInstance | null>(null)
  const captureIdRef = useRef(0)
  const recordedChunksRef = useRef<Blob[]>([])
  const recordedMimeTypeRef = useRef('')
  const recordedPcmChunksRef = useRef<Int16Array[]>([])
  const bufferedSocketAudioRef = useRef<BufferedSocketAudioState>({ bytes: 0, chunks: [] })
  const streamRef = useRef<MediaStream | null>(null)
  const isRecordingRef = useRef(false)
  const isProcessingRef = useRef(false)
  const hasMicSignalRef = useRef(false)
  const hasTranscriptRef = useRef(false)
  const transcriptSourceRef = useRef<'backend' | 'browser' | 'upload' | null>(null)
  const uploadRequestedCaptureRef = useRef<number | null>(null)
  const autoStopTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const callbacksRef = useRef<CallbacksRef>({ onResult, onPartial, onError, onLevel })
  const autoStopRef = useRef(autoStop)
  const autoStopDelayRef = useRef(autoStopDelay)
  const syncProcessingState = useCallback((nextValue: boolean) => { isProcessingRef.current = nextValue; setIsProcessing(nextValue) }, [])
  const clearAutoStopTimeout = useCallback(() => {
    if (!autoStopTimeoutRef.current) return
    clearTimeout(autoStopTimeoutRef.current); autoStopTimeoutRef.current = null
  }, [])
  const resetAudioLevel = useCallback(() => { callbacksRef.current.onLevel?.(SPEECH_IDLE_LEVEL) }, [])
  const stopBrowserRecognition = useCallback((abort = false) => {
    const recognition = browserRecognitionRef.current
    if (!recognition) return
    try {
      if (abort) recognition.abort()
      else recognition.stop()
    } catch {}
  }, [])
  const setupBrowserRecognition = useCallback((nextLanguage: string) => {
    const recognition = createBrowserSpeechRecognition(window, nextLanguage)
    if (!recognition) return
    recognition.onresult = event => {
      const chunks: string[] = []
      let isFinal = false
      for (let index = event.resultIndex; index < event.results.length; index += 1) {
        const result = event.results[index]
        const transcript = result?.[0]?.transcript?.trim()
        if (transcript) chunks.push(transcript)
        isFinal = Boolean(result?.isFinal) || isFinal
      }
      const text = chunks.join(' ').trim()
      if (!text) return
      if (transcriptSourceRef.current && transcriptSourceRef.current !== 'browser') return
      transcriptSourceRef.current = 'browser'
      hasTranscriptRef.current = true
      if (isFinal) {
        callbacksRef.current.onResult?.(text)
      } else {
        callbacksRef.current.onPartial?.(text)
      }
    }
    recognition.onend = () => { if (browserRecognitionRef.current === recognition) browserRecognitionRef.current = null }
    browserRecognitionRef.current = recognition
    try {
      recognition.start()
    } catch {
      browserRecognitionRef.current = null
    }
  }, [])
  const cleanupAudioResources = useCallback(() => {
    if (audioCaptureStopRef.current) {
      const stopAudioCapture = audioCaptureStopRef.current
      audioCaptureStopRef.current = null
      void stopAudioCapture().catch(() => {})
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop())
      streamRef.current = null
    }
  }, [])
  const stopAudioCapture = useCallback(() => {
    isRecordingRef.current = false
    clearAutoStopTimeout()
    cleanupAudioResources()
    resetBufferedSocketAudio(bufferedSocketAudioRef)
    setIsRecording(false)
    setIsReady(false)
  }, [cleanupAudioResources, clearAutoStopTimeout])
  const finishRecognitionSession = useCallback(() => {
    stopBrowserRecognition(true)
    stopAudioCapture()
    resetAudioLevel()
    syncProcessingState(false)
  }, [resetAudioLevel, stopAudioCapture, stopBrowserRecognition, syncProcessingState])
  const uploadRecordedAudio = useCallback((captureId: number) => {
    void uploadRecordedAudioTask({
      captureId,
      chunks: recordedChunksRef.current,
      mimeType: recordedMimeTypeRef.current,
      pcmChunks: recordedPcmChunksRef.current,
      getCurrentCaptureId: () => captureIdRef.current,
      getCurrentTranscriptSource: () => transcriptSourceRef.current,
      onFinish: finishRecognitionSession,
      onResult: text => {
        transcriptSourceRef.current = 'upload'
        hasTranscriptRef.current = true
        callbacksRef.current.onResult?.(text)
      },
      onError: message => {
        callbacksRef.current.onError?.(message)
      },
    })
  }, [finishRecognitionSession])
  const requestRecordedAudioFallback = useCallback((captureId: number) => (
    requestRecordedAudioFallbackTask({
      captureId,
      requestedCaptureId: uploadRequestedCaptureRef.current,
      setRequestedCaptureId: nextCaptureId => { uploadRequestedCaptureRef.current = nextCaptureId },
      recorder: mediaRecorderRef.current,
      chunks: recordedChunksRef.current,
      pcmChunks: recordedPcmChunksRef.current,
      upload: uploadRecordedAudio,
    })
  ), [uploadRecordedAudio])
  const finalizeBrowserOnlyStop = useCallback((captureId: number) => {
    if (captureId !== captureIdRef.current || !isProcessingRef.current) return
    if (hasTranscriptRef.current && transcriptSourceRef.current === 'browser') return finishRecognitionSession()
    if (requestRecordedAudioFallback(captureId)) return
    callbacksRef.current.onError?.(hasMicSignalRef.current ? SPEECH_EMPTY_RESULT_MESSAGE : SPEECH_NO_SIGNAL_MESSAGE)
    finishRecognitionSession()
  }, [finishRecognitionSession, requestRecordedAudioFallback])
  useEffect(() => {
    autoStopRef.current = autoStop
    autoStopDelayRef.current = autoStopDelay
  }, [autoStop, autoStopDelay])
  useEffect(() => {
    callbacksRef.current = { onResult, onPartial, onError, onLevel }
  }, [onError, onLevel, onPartial, onResult])
  useEffect(() => {
    if (!enabled) {
      clearAutoStopTimeout()
      cleanupAudioResources()
      setIsConnected(false)
      setIsRecording(false)
      syncProcessingState(false)
      setIsReady(false)
      isRecordingRef.current = false
      resetAudioLevel()
      resetBufferedSocketAudio(bufferedSocketAudioRef)
      return
    }
    if (!enableRealtimeRecognition) {
      setIsConnected(true)
      return () => {
        clearAutoStopTimeout()
        cleanupAudioResources()
        syncProcessingState(false)
        resetAudioLevel()
        resetBufferedSocketAudio(bufferedSocketAudioRef)
        setIsConnected(false)
        setIsRecording(false)
        setIsProcessing(false)
        setIsReady(false)
        isRecordingRef.current = false
        isProcessingRef.current = false
      }
    }
    const speechSocket = resolveSpeechSocketConfig(window.location)
    const socket = io(speechSocket.url, {
      autoConnect: false,
      path: speechSocket.path,
      transports: speechSocket.transports,
      reconnection: true,
      reconnectionAttempts: 3,    // 减少重连次数
      reconnectionDelay: 1000,    // 初始延迟 1s
      reconnectionDelayMax: 3000, // 最大延迟 3s
      timeout: 5000,             // 5秒超时
      rememberUpgrade: speechSocket.rememberUpgrade,
    })

    socket.on('connect', () => {
      setIsConnected(true)
    })
    socket.on('disconnect', (_reason: string) => {
      setIsConnected(false)
      finishRecognitionSession()
    })

    socket.on('connected', (data: ConnectedPayload) => {
      if (!data.api_configured) {
        callbacksRef.current.onError?.('API密钥未配置')
      }
    })
    socket.on('recognition_started', (_data: RecognitionStartedPayload) => {
      setIsReady(true)
    })
    socket.on('partial_result', (data: PartialResultPayload) => {
      if (data.text) {
        if (transcriptSourceRef.current && transcriptSourceRef.current !== 'backend') return
        transcriptSourceRef.current = 'backend'
        hasTranscriptRef.current = true
        callbacksRef.current.onPartial?.(data.text)
      }
    })
    socket.on('final_result', (data: FinalResultPayload) => {
      if (data.text) {
        if (transcriptSourceRef.current && transcriptSourceRef.current !== 'backend') return
        transcriptSourceRef.current = 'backend'
        hasTranscriptRef.current = true
        callbacksRef.current.onResult?.(data.text)
      }
      if (isProcessingRef.current) {
        finishRecognitionSession()
        return
      }
      if (autoStopRef.current && isRecordingRef.current) {
        clearAutoStopTimeout()
        autoStopTimeoutRef.current = setTimeout(() => {
          if (isRecordingRef.current && socketRef.current?.connected) {
            socketRef.current.emit('stop_recognition')
          }
        }, autoStopDelayRef.current)
      }
    })
    socket.on('speech_started', () => {
      // Cancel any pending auto-stop if user starts speaking again
      clearAutoStopTimeout()
    })
    socket.on('recognition_complete', () => {
      if (isProcessingRef.current && !hasTranscriptRef.current) {
        if (!hasMicSignalRef.current) {
          callbacksRef.current.onError?.(SPEECH_NO_SIGNAL_MESSAGE)
          finishRecognitionSession()
          return
        }
        if (requestRecordedAudioFallback(captureIdRef.current)) return
        callbacksRef.current.onError?.(SPEECH_EMPTY_RESULT_MESSAGE)
      }
      finishRecognitionSession()
    })
    socket.on('recognition_error', (data: RecognitionErrorPayload) => {
      console.error('[Speech] Error:', data.error)
      if (isProcessingRef.current && !hasTranscriptRef.current && !hasMicSignalRef.current) {
        callbacksRef.current.onError?.(SPEECH_NO_SIGNAL_MESSAGE)
        finishRecognitionSession()
        return
      }
      if (isProcessingRef.current && !hasTranscriptRef.current && requestRecordedAudioFallback(captureIdRef.current)) {
        return
      }
      callbacksRef.current.onError?.(data.error)
      finishRecognitionSession()
    })
    socket.on('recognition_stopped', () => {
      if (isProcessingRef.current) return
      finishRecognitionSession()
    })

    socketRef.current = socket
    const connectTimer = setTimeout(() => {
      socket.connect()
    }, 0)
    return () => {
      clearTimeout(connectTimer)
      clearAutoStopTimeout()
      cleanupAudioResources()
      syncProcessingState(false)
      resetAudioLevel()
      resetBufferedSocketAudio(bufferedSocketAudioRef)
      if (socketRef.current) {
        socketRef.current.disconnect()
        socketRef.current = null
      }
      setIsConnected(false)
      setIsRecording(false)
      setIsProcessing(false)
      setIsReady(false)
      isRecordingRef.current = false
      isProcessingRef.current = false
    }
  }, [
    cleanupAudioResources,
    clearAutoStopTimeout,
    enabled,
    finishRecognitionSession,
    resetAudioLevel,
    syncProcessingState,
    enableRealtimeRecognition,
  ])

  const startRecording = useCallback(async () => {
    if (enableRealtimeRecognition && !socketRef.current?.connected) {
      callbacksRef.current.onError?.('未连接到语音服务')
      return
    }

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      const isSecure =
        window.location.protocol === 'https:' ||
        window.location.hostname === 'localhost' ||
        window.location.hostname === '127.0.0.1'
      if (!isSecure) {
        callbacksRef.current.onError?.(
          '语音识别需要 HTTPS 安全连接。请使用 HTTPS 访问，或在本地使用 localhost。'
        )
      } else {
        callbacksRef.current.onError?.('浏览器不支持麦克风访问')
      }
      return
    }
    try {
      clearAutoStopTimeout()
      cleanupAudioResources()
      syncProcessingState(false)
      resetAudioLevel()
      hasMicSignalRef.current = false
      hasTranscriptRef.current = false
      transcriptSourceRef.current = null
      captureIdRef.current += 1
      uploadRequestedCaptureRef.current = null
      recordedChunksRef.current = []
      recordedMimeTypeRef.current = ''
      recordedPcmChunksRef.current = []
      resetBufferedSocketAudio(bufferedSocketAudioRef)
      if (enableBrowserRecognition) setupBrowserRecognition(language)
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          autoGainControl: true,
          echoCancellation: true,
          noiseSuppression: true,
        },
      })
      streamRef.current = stream
      const startedRecorder = startMediaRecorderCapture(
        window,
        stream,
        captureIdRef.current,
        chunk => {
          recordedChunksRef.current = [...recordedChunksRef.current, chunk]
        },
        (activeCaptureId, recorder) => {
          if (uploadRequestedCaptureRef.current === activeCaptureId) {
            uploadRecordedAudio(activeCaptureId)
          }
          if (mediaRecorderRef.current === recorder) {
            mediaRecorderRef.current = null
          }
        },
      )
      if (startedRecorder) {
        mediaRecorderRef.current = startedRecorder.recorder
        recordedMimeTypeRef.current = startedRecorder.mimeType
      }

      if (enableRealtimeRecognition) {
        socketRef.current?.emit('start_recognition', {
          language,
          enable_vad: enableVad,
        })
      }
      isRecordingRef.current = true
      const audioCapture = await startSpeechAudioCapture({
        stream,
        onLevel: level => {
          callbacksRef.current.onLevel?.(level)
        },
        onPcmFrame: pcmData => {
          if (!hasMicSignalRef.current && hasAudiblePcmSignal(pcmData)) hasMicSignalRef.current = true
          recordedPcmChunksRef.current.push(pcmData.slice())
          if (!enableRealtimeRecognition || !isRecordingRef.current || !socketRef.current?.connected) return
          queueBufferedSocketAudio(socketRef, bufferedSocketAudioRef, pcmData)
        },
      })
      audioCaptureStopRef.current = audioCapture.stop
      callbacksRef.current.onLevel?.(SPEECH_IDLE_LEVEL)
      setIsRecording(true)
    } catch (error: unknown) {
      console.error('[Speech] Error:', error)
      isRecordingRef.current = false
      cleanupAudioResources()
      syncProcessingState(false)
      resetAudioLevel()
      const err = error as Error & { name?: string }
      if (err.name === 'NotAllowedError') {
        callbacksRef.current.onError?.('麦克风权限被拒绝')
      } else if (err.name === 'NotFoundError') {
        callbacksRef.current.onError?.('未找到麦克风设备')
      } else {
        callbacksRef.current.onError?.('无法访问麦克风: ' + err.message)
      }
    }
  }, [
    cleanupAudioResources,
    clearAutoStopTimeout,
    enableVad,
    enableBrowserRecognition,
    enableRealtimeRecognition,
    language,
    resetAudioLevel,
    syncProcessingState,
  ])

  const stopRecording = useCallback(() => {
    if (!isRecordingRef.current && !isProcessingRef.current) {
      return
    }

    const captureId = captureIdRef.current
    if (!enableRealtimeRecognition && enableBrowserRecognition) {
      stopAudioCapture()
      syncProcessingState(true)
      callbacksRef.current.onLevel?.(0.2)
      stopBrowserRecognition()
      clearAutoStopTimeout()
      autoStopTimeoutRef.current = setTimeout(() => finalizeBrowserOnlyStop(captureId), 900)
      return
    }
    const hasRecordedAudioFallback = requestRecordedAudioFallback(captureId)
    if (enableRealtimeRecognition) flushBufferedSocketAudio(socketRef, bufferedSocketAudioRef)
    stopAudioCapture()
    if (hasTranscriptRef.current && transcriptSourceRef.current === 'browser') {
      finishRecognitionSession()
      return
    }
    if (enableRealtimeRecognition && socketRef.current?.connected) {
      syncProcessingState(true)
      callbacksRef.current.onLevel?.(0.2)
      stopBrowserRecognition()
      socketRef.current.emit('stop_recognition')
      return
    }
    if (hasRecordedAudioFallback) {
      syncProcessingState(true)
      callbacksRef.current.onLevel?.(0.2)
      stopBrowserRecognition()
      return
    }

    if (!hasMicSignalRef.current) {
      callbacksRef.current.onError?.(SPEECH_NO_SIGNAL_MESSAGE)
      finishRecognitionSession()
      return
    }
    finishRecognitionSession()
  }, [
    finishRecognitionSession,
    finalizeBrowserOnlyStop,
    requestRecordedAudioFallback,
    stopAudioCapture,
    stopBrowserRecognition,
    syncProcessingState,
    enableBrowserRecognition,
    enableRealtimeRecognition,
  ])
  return { isConnected, isRecording, isProcessing, isReady, startRecording, stopRecording }
}
export default useSpeechRecognition
