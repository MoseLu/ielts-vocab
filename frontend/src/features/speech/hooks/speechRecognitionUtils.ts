export const LOCAL_VITE_DEV_PORTS = new Set(['3000', '3020', '5173'])
export const DEFAULT_SPEECH_SOCKET_PATH = '/socket.io'
export const SPEECH_TARGET_SAMPLE_RATE = 16000
export const SPEECH_IDLE_LEVEL = 0
export const SPEECH_MIN_ACTIVE_LEVEL = 0.08
export const SPEECH_EMPTY_RESULT_MESSAGE = '未识别到清晰语音，请重试'

export interface SpeechSocketConfig {
  path: string
  rememberUpgrade: boolean
  transports: Array<'polling' | 'websocket'>
  url: string
}

export interface BrowserSpeechRecognitionResultEvent {
  resultIndex: number
  results: ArrayLike<{ 0?: { transcript?: string }; isFinal?: boolean }>
}

export interface BrowserSpeechRecognitionInstance {
  continuous: boolean
  interimResults: boolean
  lang: string
  maxAlternatives: number
  onend: (() => void) | null
  onerror: ((event: { error?: string }) => void) | null
  onresult: ((event: BrowserSpeechRecognitionResultEvent) => void) | null
  abort: () => void
  start: () => void
  stop: () => void
}

type BrowserSpeechRecognitionConstructor = new () => BrowserSpeechRecognitionInstance

export function resolveSpeechSocketConfig(location: Location): SpeechSocketConfig {
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
  const isLocalViteDevServer =
    location.protocol === 'http:' && LOCAL_VITE_DEV_PORTS.has(location.port)

  if (isLocalViteDevServer) {
    return {
      path: DEFAULT_SPEECH_SOCKET_PATH,
      rememberUpgrade: true,
      transports: ['websocket'],
      url: `${protocol}//${location.hostname}:5001/speech`,
    }
  }

  return {
    path: DEFAULT_SPEECH_SOCKET_PATH,
    rememberUpgrade: false,
    transports: ['polling'],
    url: `${protocol}//${location.host}/speech`,
  }
}

export function normalizeAudioLevel(inputData: Float32Array) {
  if (!inputData.length) return SPEECH_MIN_ACTIVE_LEVEL

  let energy = 0
  for (let i = 0; i < inputData.length; i += 1) {
    energy += inputData[i] * inputData[i]
  }

  const rms = Math.sqrt(energy / inputData.length)
  return Math.min(1, Math.max(SPEECH_MIN_ACTIVE_LEVEL, rms * 8))
}

export function encodePcm16(inputData: Float32Array, sourceSampleRate: number) {
  const targetLength = Math.max(1, Math.round(inputData.length * SPEECH_TARGET_SAMPLE_RATE / sourceSampleRate))
  const pcmData = new Int16Array(targetLength)
  const ratio = targetLength > 1 ? (inputData.length - 1) / (targetLength - 1) : 0

  for (let i = 0; i < targetLength; i += 1) {
    const sourceIndex = i * ratio
    const left = Math.floor(sourceIndex)
    const right = Math.min(left + 1, inputData.length - 1)
    const mix = sourceIndex - left
    const sample = inputData[left] + (inputData[right] - inputData[left]) * mix
    const clamped = Math.max(-1, Math.min(1, sample))
    pcmData[i] = clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff
  }

  return pcmData
}

function resolveBrowserRecognitionLanguage(language: string) {
  if (language.startsWith('zh')) return 'zh-CN'
  if (language.startsWith('en')) return 'en-US'
  return language
}

export function createBrowserSpeechRecognition(
  windowObject: Window & typeof globalThis,
  language: string,
) {
  const recognitionCtor = (
    windowObject as Window & typeof globalThis & {
      SpeechRecognition?: BrowserSpeechRecognitionConstructor
      webkitSpeechRecognition?: BrowserSpeechRecognitionConstructor
    }
  ).SpeechRecognition ?? (
    windowObject as Window & typeof globalThis & {
      webkitSpeechRecognition?: BrowserSpeechRecognitionConstructor
    }
  ).webkitSpeechRecognition

  if (!recognitionCtor) return null

  const recognition = new recognitionCtor()
  recognition.continuous = true
  recognition.interimResults = true
  recognition.maxAlternatives = 1
  recognition.lang = resolveBrowserRecognitionLanguage(language)
  return recognition
}
