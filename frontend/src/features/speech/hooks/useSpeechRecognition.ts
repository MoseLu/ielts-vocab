import { useState, useRef, useCallback, useEffect } from 'react'
import { io, Socket } from 'socket.io-client'
import {
  createBrowserSpeechRecognition,
  encodePcm16,
  normalizeAudioLevel,
  resolveSpeechSocketConfig,
  SPEECH_EMPTY_RESULT_MESSAGE,
  SPEECH_IDLE_LEVEL,
  SPEECH_MIN_ACTIVE_LEVEL,
  type BrowserSpeechRecognitionInstance,
} from './speechRecognitionUtils'

export interface SpeechRecognitionOptions {
  /** Whether the socket connection should be active */
  enabled?: boolean
  /** Language code (default: 'zh') */
  language?: string
  /** Enable voice activity detection (default: true) */
  enableVad?: boolean
  /** Auto-stop after final result (default: true) */
  autoStop?: boolean
  /** Delay before auto-stop in ms (default: 1500) */
  autoStopDelay?: number
  /** Callback when final recognition result is available */
  onResult?: (text: string) => void
  /** Callback when partial recognition result is available */
  onPartial?: (text: string) => void
  /** Callback when an error occurs */
  onError?: (error: string) => void
  /** Callback with a normalized input level between 0 and 1 */
  onLevel?: (level: number) => void
}

export interface UseSpeechRecognitionReturn {
  /** Whether the socket is connected to the server */
  isConnected: boolean
  /** Whether audio is currently being recorded and sent */
  isRecording: boolean
  /** Whether the backend is still finishing speech-to-text */
  isProcessing: boolean
  /** Whether the recognition session is ready to receive audio */
  isReady: boolean
  /** Start recording and speech recognition */
  startRecording: () => Promise<void>
  /** Stop recording and speech recognition */
  stopRecording: () => void
}
interface CallbacksRef {
  onResult?: (text: string) => void
  onPartial?: (text: string) => void
  onError?: (error: string) => void
  onLevel?: (level: number) => void
}
interface ConnectedPayload {
  api_configured: boolean
}
interface RecognitionStartedPayload {
  session_id?: string
}
interface PartialResultPayload {
  text: string
}
interface FinalResultPayload {
  text: string
}
interface RecognitionErrorPayload {
  error: string
}
export function useSpeechRecognition({
  enabled = true,
  language = 'zh',
  enableVad = true,
  autoStop = true,
  autoStopDelay = 1500,
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
  const audioContextRef = useRef<AudioContext | null>(null)
  const processorRef = useRef<ScriptProcessorNode | null>(null)
  const browserRecognitionRef = useRef<BrowserSpeechRecognitionInstance | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const isRecordingRef = useRef(false)
  const isProcessingRef = useRef(false)
  const hasTranscriptRef = useRef(false)
  const transcriptSourceRef = useRef<'backend' | 'browser' | null>(null)
  const autoStopTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  // Use refs to keep callbacks fresh without triggering re-renders
  const callbacksRef = useRef<CallbacksRef>({ onResult, onPartial, onError, onLevel })
  const autoStopRef = useRef(autoStop)
  const autoStopDelayRef = useRef(autoStopDelay)

  const syncProcessingState = useCallback((nextValue: boolean) => {
    isProcessingRef.current = nextValue
    setIsProcessing(nextValue)
  }, [])

  const clearAutoStopTimeout = useCallback(() => {
    if (autoStopTimeoutRef.current) {
      clearTimeout(autoStopTimeoutRef.current)
      autoStopTimeoutRef.current = null
    }
  }, [])

  const resetAudioLevel = useCallback(() => {
    callbacksRef.current.onLevel?.(SPEECH_IDLE_LEVEL)
  }, [])

  const stopBrowserRecognition = useCallback((abort = false) => {
    const recognition = browserRecognitionRef.current
    if (!recognition) return
    try {
      if (abort) {
        recognition.abort()
      } else {
        recognition.stop()
      }
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

    recognition.onend = () => {
      if (browserRecognitionRef.current === recognition) {
        browserRecognitionRef.current = null
      }
    }

    browserRecognitionRef.current = recognition
    try {
      recognition.start()
    } catch {
      browserRecognitionRef.current = null
    }
  }, [])

  const cleanupAudioResources = useCallback(() => {
    if (processorRef.current) {
      processorRef.current.onaudioprocess = null
      processorRef.current.disconnect()
      processorRef.current = null
    }

    if (audioContextRef.current) {
      const audioContext = audioContextRef.current
      audioContextRef.current = null
      void audioContext.close().catch(() => {})
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
    setIsRecording(false)
    setIsReady(false)
  }, [cleanupAudioResources, clearAutoStopTimeout])

  const finishRecognitionSession = useCallback(() => {
    stopBrowserRecognition(true)
    stopAudioCapture()
    resetAudioLevel()
    syncProcessingState(false)
  }, [resetAudioLevel, stopAudioCapture, stopBrowserRecognition, syncProcessingState])

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
      return
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
        callbacksRef.current.onError?.(SPEECH_EMPTY_RESULT_MESSAGE)
      }
      finishRecognitionSession()
    })

    socket.on('recognition_error', (data: RecognitionErrorPayload) => {
      console.error('[Speech] Error:', data.error)
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
  ])

  const startRecording = useCallback(async () => {
    if (!socketRef.current?.connected) {
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
      hasTranscriptRef.current = false
      transcriptSourceRef.current = null
      setupBrowserRecognition(language)

      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          autoGainControl: true,
          echoCancellation: true,
          noiseSuppression: true,
        },
      })

      streamRef.current = stream

      const audioContext = new AudioContext()
      if (audioContext.state === 'suspended') {
        await audioContext.resume()
      }
      audioContextRef.current = audioContext

      const source = audioContext.createMediaStreamSource(stream)
      const processor = audioContext.createScriptProcessor(4096, 1, 1)
      processorRef.current = processor

      socketRef.current.emit('start_recognition', {
        language,
        enable_vad: enableVad,
      })

      processor.onaudioprocess = (event: AudioProcessingEvent) => {
        if (isRecordingRef.current && socketRef.current?.connected) {
          const inputData = event.inputBuffer.getChannelData(0)
          callbacksRef.current.onLevel?.(normalizeAudioLevel(inputData))
          const pcmData = encodePcm16(inputData, audioContext.sampleRate)
          const uint8Data = new Uint8Array(pcmData.buffer)
          socketRef.current.emit('audio_data', uint8Data)
        }
      }

      source.connect(processor)
      processor.connect(audioContext.destination)

      callbacksRef.current.onLevel?.(SPEECH_MIN_ACTIVE_LEVEL)
      setIsRecording(true)
      isRecordingRef.current = true
    } catch (error: unknown) {
      console.error('[Speech] Error:', error)
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
    language,
    resetAudioLevel,
    syncProcessingState,
  ])

  const stopRecording = useCallback(() => {
    if (!isRecordingRef.current && !isProcessingRef.current) {
      return
    }

    stopAudioCapture()

    if (socketRef.current?.connected) {
      syncProcessingState(true)
      callbacksRef.current.onLevel?.(0.2)
      stopBrowserRecognition()
      socketRef.current.emit('stop_recognition')
      return
    }

    finishRecognitionSession()
  }, [finishRecognitionSession, stopAudioCapture, stopBrowserRecognition, syncProcessingState])

  return {
    isConnected,
    isRecording,
    isProcessing,
    isReady,
    startRecording,
    stopRecording,
  }
}

export default useSpeechRecognition
