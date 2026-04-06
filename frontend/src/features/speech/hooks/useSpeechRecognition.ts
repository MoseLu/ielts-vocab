import { useState, useRef, useCallback, useEffect } from 'react'
import { io, Socket } from 'socket.io-client'

/**
 * Custom hook for real-time speech recognition using DashScope qwen3-asr
 */

// ============================================================================
// Type Definitions
// ============================================================================

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
}

export interface UseSpeechRecognitionReturn {
  /** Whether the socket is connected to the server */
  isConnected: boolean
  /** Whether audio is currently being recorded and sent */
  isRecording: boolean
  /** Whether the recognition session is ready to receive audio */
  isReady: boolean
  /** Start recording and speech recognition */
  startRecording: () => Promise<void>
  /** Stop recording and speech recognition */
  stopRecording: () => void
}

// Internal callback container stored in a ref to avoid stale closures
interface CallbacksRef {
  onResult?: (text: string) => void
  onPartial?: (text: string) => void
  onError?: (error: string) => void
}

// Socket event payload types
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

const LOCAL_VITE_DEV_PORTS = new Set(['3000', '3020', '5173'])
const DEFAULT_SPEECH_SOCKET_PATH = '/socket.io'
const PROXIED_SPEECH_SOCKET_PATH = '/speech-socket.io'

interface SpeechSocketConfig {
  path: string
  url: string
}

function resolveSpeechSocketConfig(location: Location): SpeechSocketConfig {
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
  const isLocalViteDevServer =
    location.protocol === 'http:' && LOCAL_VITE_DEV_PORTS.has(location.port)

  if (isLocalViteDevServer) {
    return {
      path: DEFAULT_SPEECH_SOCKET_PATH,
      url: `${protocol}//${location.hostname}:5001/speech`,
    }
  }

  return {
    path: PROXIED_SPEECH_SOCKET_PATH,
    url: `${protocol}//${location.host}/speech`,
  }
}

// ============================================================================
// Hook Implementation
// ============================================================================

export function useSpeechRecognition({
  enabled = true,
  language = 'zh',
  enableVad = true,
  autoStop = true,
  autoStopDelay = 1500,
  onResult,
  onPartial,
  onError,
}: SpeechRecognitionOptions): UseSpeechRecognitionReturn {
  const [isConnected, setIsConnected] = useState(false)
  const [isRecording, setIsRecording] = useState(false)
  const [isReady, setIsReady] = useState(false)

  const socketRef = useRef<Socket | null>(null)
  const audioContextRef = useRef<AudioContext | null>(null)
  const processorRef = useRef<ScriptProcessorNode | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const isRecordingRef = useRef(false)
  const autoStopTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Use refs to keep callbacks fresh without triggering re-renders
  const callbacksRef = useRef<CallbacksRef>({ onResult, onPartial, onError })
  const autoStopRef = useRef(autoStop)
  const autoStopDelayRef = useRef(autoStopDelay)

  useEffect(() => {
    autoStopRef.current = autoStop
    autoStopDelayRef.current = autoStopDelay
  }, [autoStop, autoStopDelay])

  useEffect(() => {
    callbacksRef.current = { onResult, onPartial, onError }
  }, [onResult, onPartial, onError])

  // Initialize socket once on mount
  useEffect(() => {
    if (!enabled) {
      setIsConnected(false)
      setIsRecording(false)
      setIsReady(false)
      isRecordingRef.current = false
      return
    }

    // Local Vite dev mode talks to the speech service directly because the
    // dev proxy intermittently corrupts websocket frames on browser clients.
    // Preview/prod stay same-origin, but use a custom proxy path so speech
    // traffic goes through the preview server instead of a stale system nginx
    // /socket.io route that may still point at the main Flask app.
    const speechSocket = resolveSpeechSocketConfig(window.location)
    const socket = io(speechSocket.url, {
      autoConnect: false,
      path: speechSocket.path,
      transports: ['websocket'],  // 优先 WebSocket，减少轮询开销
      reconnection: true,
      reconnectionAttempts: 3,    // 减少重连次数
      reconnectionDelay: 1000,    // 初始延迟 1s
      reconnectionDelayMax: 3000, // 最大延迟 3s
      timeout: 5000,             // 5秒超时
      rememberUpgrade: true,      // 记住上次的传输方式
    })

    socket.on('connect', () => {
      setIsConnected(true)
    })

    socket.on('disconnect', (_reason: string) => {
      setIsConnected(false)
      setIsReady(false)
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
        callbacksRef.current.onPartial?.(data.text)
      }
    })

    socket.on('final_result', (data: FinalResultPayload) => {
      if (data.text) {
        callbacksRef.current.onResult?.(data.text)
      }
      // Auto-stop after final result if enabled
      if (autoStopRef.current && isRecordingRef.current) {
        // Clear any existing timeout
        if (autoStopTimeoutRef.current) {
          clearTimeout(autoStopTimeoutRef.current)
        }
        // Stop after a short delay
        autoStopTimeoutRef.current = setTimeout(() => {
          if (isRecordingRef.current && socketRef.current?.connected) {
            socketRef.current.emit('stop_recognition')
          }
        }, autoStopDelayRef.current)
      }
    })

    socket.on('speech_started', () => {
      // Cancel any pending auto-stop if user starts speaking again
      if (autoStopTimeoutRef.current) {
        clearTimeout(autoStopTimeoutRef.current)
        autoStopTimeoutRef.current = null
      }
    })

    socket.on('recognition_complete', () => {
      setIsRecording(false)
      setIsReady(false)
      isRecordingRef.current = false
    })

    socket.on('recognition_error', (data: RecognitionErrorPayload) => {
      console.error('[Speech] Error:', data.error)
      callbacksRef.current.onError?.(data.error)
      setIsRecording(false)
      isRecordingRef.current = false
    })

    socket.on('recognition_stopped', () => {
      setIsRecording(false)
      setIsReady(false)
      isRecordingRef.current = false
    })

    socketRef.current = socket
    // Defer the first connect by one task so React StrictMode's dev-only
    // mount/unmount cycle does not start a websocket that is immediately closed.
    const connectTimer = setTimeout(() => {
      socket.connect()
    }, 0)

    // Cleanup on unmount
    return () => {
      clearTimeout(connectTimer)
      // Clear auto-stop timeout
      if (autoStopTimeoutRef.current) {
        clearTimeout(autoStopTimeoutRef.current)
        autoStopTimeoutRef.current = null
      }
      // Stop audio
      if (processorRef.current) {
        processorRef.current.disconnect()
        processorRef.current = null
      }
      if (audioContextRef.current) {
        audioContextRef.current.close()
        audioContextRef.current = null
      }
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(t => t.stop())
        streamRef.current = null
      }
      // Disconnect socket
      if (socketRef.current) {
        socketRef.current.disconnect()
        socketRef.current = null
      }
      setIsConnected(false)
      setIsRecording(false)
      setIsReady(false)
      isRecordingRef.current = false
    }
  }, [enabled])

  // Start recording
  const startRecording = useCallback(async () => {
    if (!socketRef.current?.connected) {
      callbacksRef.current.onError?.('未连接到语音服务')
      return
    }

    // Check for secure context (HTTPS required for microphone access)
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
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: 16000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
        },
      })

      streamRef.current = stream

      const audioContext = new AudioContext({ sampleRate: 16000 })
      if (audioContext.state === 'suspended') {
        await audioContext.resume()
      }
      audioContextRef.current = audioContext

      const source = audioContext.createMediaStreamSource(stream)
      const processor = audioContext.createScriptProcessor(4096, 1, 1)
      processorRef.current = processor

      // Start recognition session
      socketRef.current.emit('start_recognition', {
        language,
        enable_vad: enableVad,
      })

      // Handle audio data
      processor.onaudioprocess = (event: AudioProcessingEvent) => {
        if (isRecordingRef.current && socketRef.current?.connected) {
          const inputData = event.inputBuffer.getChannelData(0)
          // Convert float32 to int16 PCM
          const pcmData = new Int16Array(inputData.length)
          for (let i = 0; i < inputData.length; i++) {
            const s = Math.max(-1, Math.min(1, inputData[i]))
            pcmData[i] = s < 0 ? s * 0x8000 : s * 0x7fff
          }
          // Send as Uint8Array for proper binary transfer
          const uint8Data = new Uint8Array(pcmData.buffer)
          socketRef.current.emit('audio_data', uint8Data)
        }
      }

      source.connect(processor)
      processor.connect(audioContext.destination)

      setIsRecording(true)
      isRecordingRef.current = true
    } catch (error: unknown) {
      console.error('[Speech] Error:', error)
      const err = error as Error & { name?: string }
      if (err.name === 'NotAllowedError') {
        callbacksRef.current.onError?.('麦克风权限被拒绝')
      } else if (err.name === 'NotFoundError') {
        callbacksRef.current.onError?.('未找到麦克风设备')
      } else {
        callbacksRef.current.onError?.('无法访问麦克风: ' + err.message)
      }
    }
  }, [language, enableVad])

  // Stop recording
  const stopRecording = useCallback(() => {
    isRecordingRef.current = false

    // Clear auto-stop timeout
    if (autoStopTimeoutRef.current) {
      clearTimeout(autoStopTimeoutRef.current)
      autoStopTimeoutRef.current = null
    }

    if (processorRef.current) {
      processorRef.current.disconnect()
      processorRef.current = null
    }

    if (audioContextRef.current) {
      audioContextRef.current.close()
      audioContextRef.current = null
    }

    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop())
      streamRef.current = null
    }

    if (socketRef.current?.connected) {
      socketRef.current.emit('stop_recognition')
    }

    setIsRecording(false)
  }, [])

  return {
    isConnected,
    isRecording,
    isReady,
    startRecording,
    stopRecording,
  }
}

export default useSpeechRecognition
