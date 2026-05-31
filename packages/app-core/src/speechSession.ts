export type SpeechSessionStatus =
  | 'idle'
  | 'connecting'
  | 'ready'
  | 'recording'
  | 'processing'
  | 'completed'
  | 'error'

export interface SpeechSessionState {
  error: string
  finalText: string
  level: number
  partialText: string
  recognitionId: number
  status: SpeechSessionStatus
}

export type SpeechSessionEvent =
  | { type: 'connect' }
  | { type: 'ready' }
  | { type: 'start_recording'; recognitionId: number }
  | { type: 'level'; level: number }
  | { type: 'partial'; text: string }
  | { type: 'stop_recording' }
  | { type: 'final'; text: string }
  | { type: 'error'; message: string }
  | { type: 'reset' }

export const initialSpeechSessionState: SpeechSessionState = {
  error: '',
  finalText: '',
  level: 0,
  partialText: '',
  recognitionId: 0,
  status: 'idle',
}

export function reduceSpeechSession(
  state: SpeechSessionState,
  event: SpeechSessionEvent,
): SpeechSessionState {
  switch (event.type) {
    case 'connect':
      return { ...state, error: '', status: state.status === 'recording' ? 'recording' : 'connecting' }
    case 'ready':
      return { ...state, error: '', status: state.status === 'recording' ? 'recording' : 'ready' }
    case 'start_recording':
      return {
        ...initialSpeechSessionState,
        recognitionId: event.recognitionId,
        status: 'recording',
      }
    case 'level':
      return { ...state, level: Math.max(0, Math.min(1, event.level)) }
    case 'partial':
      return { ...state, partialText: event.text, status: 'recording' }
    case 'stop_recording':
      return { ...state, level: 0, status: 'processing' }
    case 'final':
      return { ...state, finalText: event.text, level: 0, status: 'completed' }
    case 'error':
      return {
        ...state,
        error: event.message,
        level: 0,
        status: state.status === 'recording' ? 'recording' : 'error',
      }
    case 'reset':
      return initialSpeechSessionState
  }
}
