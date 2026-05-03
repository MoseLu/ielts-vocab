import { useCallback, useEffect, useReducer, useRef } from 'react'
import { PermissionsAndroid, Platform } from 'react-native'
import { io, type Socket } from 'socket.io-client'
import { initialSpeechSessionState, reduceSpeechSession } from '@ielts-vocab/app-core'
import { mobileApiClient } from '../api/mobileApi'
import { apiBaseUrl } from '../config'
import {
  audioCaptureEvents,
  configureNativeAudioSession,
  startNativePcmCapture,
  stopNativePcmCapture,
} from '../native/NativeAudioBridge'

type SpeechSocket = Socket<{
  connected: (payload: { authenticated?: boolean; user_id?: number | string | null }) => void
  recognition_started: (payload: { recognition_id?: number }) => void
  partial_result: (payload: { recognition_id?: number; text?: string }) => void
  final_result: (payload: { recognition_id?: number; text?: string }) => void
  recognition_complete: (payload: { recognition_id?: number }) => void
  recognition_error: (payload: { error?: string; recognition_id?: number }) => void
}, {
  audio_data: (payload: {
    base64Pcm: string
    channels: number
    encoding: 'pcm16'
    sampleRate: number
  }) => void
  commit_audio_buffer: () => void
  start_recognition: (payload: { enable_vad: boolean; language: string; recognition_id: number }) => void
  stop_recognition: () => void
}>

type NativePcmFrame = {
  base64Pcm: string
  channels?: number
  encoding?: 'pcm16'
  sampleRate: number
}

async function ensureMicrophonePermission() {
  if (Platform.OS !== 'android') return
  const permission = PermissionsAndroid.PERMISSIONS.RECORD_AUDIO
  const hasPermission = await PermissionsAndroid.check(permission)
  if (hasPermission) return
  const result = await PermissionsAndroid.request(permission)
  if (result !== PermissionsAndroid.RESULTS.GRANTED) {
    throw new Error('麦克风权限未开启')
  }
}

function isCurrentRecognition(recognitionId: number, payload: { recognition_id?: number }) {
  return payload.recognition_id === undefined || payload.recognition_id === recognitionId
}

export function useMobileSpeechRecognition(language = 'en') {
  const [state, dispatch] = useReducer(reduceSpeechSession, initialSpeechSessionState)
  const recognitionIdRef = useRef(0)
  const socketRef = useRef<SpeechSocket | null>(null)

  const disconnectSocket = useCallback(() => {
    socketRef.current?.disconnect()
    socketRef.current = null
  }, [])

  useEffect(() => () => {
    void stopNativePcmCapture().catch(() => undefined)
    disconnectSocket()
  }, [disconnectSocket])

  const connectSocket = useCallback(async (recognitionId: number) => {
    const token = await mobileApiClient.getAccessToken()
    if (!token) throw new Error('请先登录')
    disconnectSocket()
    dispatch({ type: 'connect' })
    const socket: SpeechSocket = io(`${apiBaseUrl}/speech`, {
      auth: { token },
      path: '/socket.io',
      reconnection: true,
      reconnectionAttempts: 3,
      timeout: 8000,
      transports: ['websocket', 'polling'],
    })
    socketRef.current = socket
    socket.on('connected', () => dispatch({ type: 'ready' }))
    socket.on('recognition_started', payload => {
      if (isCurrentRecognition(recognitionId, payload)) dispatch({ type: 'ready' })
    })
    socket.on('partial_result', payload => {
      if (payload.text && isCurrentRecognition(recognitionId, payload)) {
        dispatch({ type: 'partial', text: payload.text })
      }
    })
    socket.on('final_result', payload => {
      if (payload.text && isCurrentRecognition(recognitionId, payload)) {
        dispatch({ type: 'final', text: payload.text })
      }
    })
    socket.on('recognition_complete', payload => {
      if (isCurrentRecognition(recognitionId, payload)) dispatch({ type: 'stop_recording' })
    })
    socket.on('recognition_error', payload => {
      if (isCurrentRecognition(recognitionId, payload)) {
        dispatch({ type: 'error', message: payload.error || '语音识别失败' })
      }
    })
    socket.on('connect_error', error => {
      dispatch({ type: 'error', message: error.message || '语音服务连接失败' })
    })
    return socket
  }, [disconnectSocket])

  const start = useCallback(async () => {
    const recognitionId = Date.now()
    recognitionIdRef.current = recognitionId
    dispatch({ type: 'start_recording', recognitionId })
    let levelSubscription: { remove: () => void } | undefined
    let pcmSubscription: { remove: () => void } | undefined
    try {
      const socket = await connectSocket(recognitionId)
      await ensureMicrophonePermission()
      await configureNativeAudioSession()

      levelSubscription = audioCaptureEvents?.addListener('ieltsAudioLevel', (level: number) => {
        dispatch({ type: 'level', level })
      })
      pcmSubscription = audioCaptureEvents?.addListener('ieltsPcmFrame', (frame: NativePcmFrame) => {
        if (socket.connected && frame.base64Pcm) {
          socket.emit('audio_data', {
            base64Pcm: frame.base64Pcm,
            channels: frame.channels || 1,
            encoding: frame.encoding || 'pcm16',
            sampleRate: frame.sampleRate || 16000,
          })
        }
      })

      socket.emit('start_recognition', {
        enable_vad: true,
        language,
        recognition_id: recognitionId,
      })
      await startNativePcmCapture()
    } catch (error) {
      levelSubscription?.remove()
      pcmSubscription?.remove()
      await stopNativePcmCapture().catch(() => undefined)
      disconnectSocket()
      dispatch({ type: 'error', message: error instanceof Error ? error.message : '无法开始录音' })
      throw error
    }

    return () => {
      levelSubscription?.remove()
      pcmSubscription?.remove()
    }
  }, [connectSocket, disconnectSocket, language])

  const stop = useCallback(async () => {
    dispatch({ type: 'stop_recording' })
    await stopNativePcmCapture()
    socketRef.current?.emit('commit_audio_buffer')
    socketRef.current?.emit('stop_recognition')
  }, [])

  return {
    start,
    state,
    stop,
  }
}
