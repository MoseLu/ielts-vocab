import { useState, useRef, useCallback, useEffect } from 'react'
import { io } from 'socket.io-client'

/**
 * Custom hook for real-time speech recognition using DashScope qwen3-asr
 */
export function useSpeechRecognition({
  language = 'zh',
  enableVad = true,
  onResult,
  onPartial,
  onError,
}) {
  const [isConnected, setIsConnected] = useState(false)
  const [isRecording, setIsRecording] = useState(false)
  const [isReady, setIsReady] = useState(false)

  const socketRef = useRef(null)
  const audioContextRef = useRef(null)
  const processorRef = useRef(null)
  const streamRef = useRef(null)
  const isRecordingRef = useRef(false)
  const mountedRef = useRef(false)

  // Use refs to keep callbacks fresh without triggering re-renders
  const callbacksRef = useRef({ onResult, onPartial, onError })
  useEffect(() => {
    callbacksRef.current = { onResult, onPartial, onError }
  }, [onResult, onPartial, onError])

  // Initialize socket once on mount
  useEffect(() => {
    if (mountedRef.current) return
    mountedRef.current = true

    console.log('[Speech] Initializing socket...')

    // 使用相对路径，通过 Vite 代理转发
    // 支持远程访问（内网穿透）
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host  // 使用当前页面的 host（包含端口）
    const speechUrl = `${protocol}//${host}`

    console.log('[Speech] Connecting to:', speechUrl)

    const socket = io(`${speechUrl}/speech`, {
      transports: ['websocket'],
      reconnection: true,
      reconnectionAttempts: 5,
      reconnectionDelay: 2000,
      reconnectionDelayMax: 5000,
      timeout: 20000,
    })

    socket.on('connect', () => {
      console.log('[Speech] Connected to server')
      setIsConnected(true)
    })

    socket.on('disconnect', (reason) => {
      console.log('[Speech] Disconnected:', reason)
      setIsConnected(false)
      setIsReady(false)
    })

    socket.on('connected', (data) => {
      console.log('[Speech] Server confirmed:', data)
      if (!data.api_configured) {
        callbacksRef.current.onError?.('API密钥未配置')
      }
    })

    socket.on('recognition_started', (data) => {
      console.log('[Speech] Recognition started:', data)
      setIsReady(true)
    })

    // Catch all events for debugging
    socket.onAny((eventName, ...args) => {
      console.log('[Speech] Event received:', eventName, args)
    })

    socket.on('partial_result', (data) => {
      if (data.text) {
        callbacksRef.current.onPartial?.(data.text)
      }
    })

    socket.on('final_result', (data) => {
      console.log('[Speech] Final result received:', data)
      if (data.text) {
        callbacksRef.current.onResult?.(data.text)
      }
    })

    socket.on('recognition_complete', () => {
      console.log('[Speech] Recognition complete')
      setIsRecording(false)
      setIsReady(false)
      isRecordingRef.current = false
    })

    socket.on('recognition_error', (data) => {
      console.error('[Speech] Error:', data.error)
      callbacksRef.current.onError?.(data.error)
      setIsRecording(false)
      isRecordingRef.current = false
    })

    socket.on('recognition_stopped', () => {
      console.log('[Speech] Recognition stopped')
      setIsRecording(false)
      setIsReady(false)
      isRecordingRef.current = false
    })

    socketRef.current = socket

    // Cleanup on unmount
    return () => {
      console.log('[Speech] Cleaning up...')
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
      mountedRef.current = false
    }
  }, []) // Empty deps - only run once

  // Start recording
  const startRecording = useCallback(async () => {
    if (!socketRef.current?.connected) {
      onError?.('未连接到语音服务')
      return
    }

    // Check for secure context (HTTPS required for microphone access)
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      const isSecure = window.location.protocol === 'https:' || window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
      if (!isSecure) {
        onError?.('语音识别需要 HTTPS 安全连接。请使用 HTTPS 访问，或在本地使用 localhost。')
      } else {
        onError?.('浏览器不支持麦克风访问')
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
      processor.onaudioprocess = (event) => {
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
          console.log('[Speech] Sending audio chunk:', uint8Data.byteLength, 'bytes')
          socketRef.current.emit('audio_data', uint8Data)
        }
      }

      source.connect(processor)
      processor.connect(audioContext.destination)

      setIsRecording(true)
      isRecordingRef.current = true
      console.log('[Speech] Started recording')

    } catch (error) {
      console.error('[Speech] Error:', error)
      if (error.name === 'NotAllowedError') {
        onError?.('麦克风权限被拒绝')
      } else if (error.name === 'NotFoundError') {
        onError?.('未找到麦克风设备')
      } else {
        onError?.('无法访问麦克风: ' + error.message)
      }
    }
  }, [language, enableVad])

  // Stop recording
  const stopRecording = useCallback(() => {
    isRecordingRef.current = false

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
    console.log('[Speech] Stopped recording')
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