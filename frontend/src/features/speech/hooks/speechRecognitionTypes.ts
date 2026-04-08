export interface SpeechRecognitionOptions {
  enabled?: boolean
  language?: string
  enableVad?: boolean
  autoStop?: boolean
  autoStopDelay?: number
  onResult?: (text: string) => void
  onPartial?: (text: string) => void
  onError?: (error: string) => void
  onLevel?: (level: number) => void
}

export interface UseSpeechRecognitionReturn {
  isConnected: boolean
  isRecording: boolean
  isProcessing: boolean
  isReady: boolean
  startRecording: () => Promise<void>
  stopRecording: () => void
}

export interface CallbacksRef {
  onResult?: (text: string) => void
  onPartial?: (text: string) => void
  onError?: (error: string) => void
  onLevel?: (level: number) => void
}

export interface ConnectedPayload {
  api_configured: boolean
}

export interface RecognitionStartedPayload {
  session_id?: string
}

export interface PartialResultPayload {
  text: string
}

export interface FinalResultPayload {
  text: string
}

export interface RecognitionErrorPayload {
  error: string
}
