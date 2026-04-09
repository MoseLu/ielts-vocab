export const LOCAL_VITE_DEV_PORTS = new Set(['3000', '3020', '5173'])
export const DEFAULT_SPEECH_SOCKET_PATH = '/socket.io'
export const SPEECH_TARGET_SAMPLE_RATE = 16000
export const SPEECH_IDLE_LEVEL = 0
export const SPEECH_MIN_ACTIVE_LEVEL = 0.02
export const SPEECH_REALTIME_PCM_BATCH_BYTES = 3200
export const SPEECH_EMPTY_RESULT_MESSAGE = '未识别到清晰语音，请重试'
export const SPEECH_NO_SIGNAL_MESSAGE = '未检测到麦克风输入，请检查系统麦克风和浏览器权限'
const REMOTE_SPEECH_TRANSPORTS: Array<'polling' | 'websocket'> = ['websocket', 'polling']
const SPEECH_LEVEL_SILENCE_FLOOR = 0.0018
const SPEECH_LEVEL_DB_FLOOR = -54
const SPEECH_LEVEL_DB_CEILING = -10

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
const MEDIA_RECORDER_MIME_CANDIDATES = [
  'audio/webm;codecs=opus',
  'audio/webm',
  'audio/ogg;codecs=opus',
  'audio/mp4',
]

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
    rememberUpgrade: true,
    transports: REMOTE_SPEECH_TRANSPORTS,
    url: `${protocol}//${location.host}/speech`,
  }
}

export function normalizeAudioLevel(inputData: Float32Array) {
  if (!inputData.length) return SPEECH_IDLE_LEVEL

  let energy = 0
  let peak = 0
  for (let i = 0; i < inputData.length; i += 1) {
    const sample = inputData[i]
    const absoluteSample = Math.abs(sample)
    if (absoluteSample > peak) peak = absoluteSample
    energy += sample * sample
  }

  const rms = Math.sqrt(energy / inputData.length)
  if (peak < SPEECH_LEVEL_SILENCE_FLOOR && rms < SPEECH_LEVEL_SILENCE_FLOOR) {
    return SPEECH_IDLE_LEVEL
  }

  const rmsDb = 20 * Math.log10(Math.max(rms, 0.00001))
  const normalizedDb = Math.min(1, Math.max(0, (rmsDb - SPEECH_LEVEL_DB_FLOOR) / (SPEECH_LEVEL_DB_CEILING - SPEECH_LEVEL_DB_FLOOR)))
  const normalizedPeak = Math.min(1, Math.max(0, peak * 8.6))
  const combinedLevel = normalizedDb * 0.58 + normalizedPeak * 0.42
  const boostedLevel = Math.pow(combinedLevel, 0.54)

  if (boostedLevel <= 0.01) return SPEECH_IDLE_LEVEL
  return Math.min(1, Math.max(SPEECH_MIN_ACTIVE_LEVEL, boostedLevel))
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

export function buildWavBlobFromPcmChunks(chunks: Int16Array[], sampleRate = SPEECH_TARGET_SAMPLE_RATE) {
  const normalizedChunks = chunks.filter(chunk => chunk.length > 0)
  const totalSamples = normalizedChunks.reduce((sum, chunk) => sum + chunk.length, 0)
  const wavBuffer = new ArrayBuffer(44 + totalSamples * 2)
  const view = new DataView(wavBuffer)

  const writeAscii = (offset: number, value: string) => {
    for (let index = 0; index < value.length; index += 1) {
      view.setUint8(offset + index, value.charCodeAt(index))
    }
  }

  writeAscii(0, 'RIFF')
  view.setUint32(4, 36 + totalSamples * 2, true)
  writeAscii(8, 'WAVE')
  writeAscii(12, 'fmt ')
  view.setUint32(16, 16, true)
  view.setUint16(20, 1, true)
  view.setUint16(22, 1, true)
  view.setUint32(24, sampleRate, true)
  view.setUint32(28, sampleRate * 2, true)
  view.setUint16(32, 2, true)
  view.setUint16(34, 16, true)
  writeAscii(36, 'data')
  view.setUint32(40, totalSamples * 2, true)

  let offset = 44
  for (const chunk of normalizedChunks) {
    for (let index = 0; index < chunk.length; index += 1) {
      view.setInt16(offset, chunk[index], true)
      offset += 2
    }
  }

  return new Blob([wavBuffer], { type: 'audio/wav' })
}

export function buildPcmPayloadFromChunks(chunks: Int16Array[]) {
  const normalizedChunks = chunks.filter(chunk => chunk.length > 0)
  const totalSamples = normalizedChunks.reduce((sum, chunk) => sum + chunk.length, 0)
  const merged = new Int16Array(totalSamples)
  let offset = 0

  for (const chunk of normalizedChunks) {
    merged.set(chunk, offset)
    offset += chunk.length
  }

  return new Uint8Array(merged.buffer)
}

export function hasAudiblePcmSignal(pcmData: Int16Array, threshold = 16) {
  return pcmData.some(sample => Math.abs(sample) > threshold)
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

export function resolveMediaRecorderMimeType(windowObject: Window & typeof globalThis) {
  const recorder = windowObject.MediaRecorder
  if (!recorder?.isTypeSupported) return ''
  return MEDIA_RECORDER_MIME_CANDIDATES.find(type => recorder.isTypeSupported(type)) ?? ''
}

export function buildRecordedAudioFilename(mimeType: string) {
  if (mimeType.includes('ogg')) return 'speech-input.ogg'
  if (mimeType.includes('mp4') || mimeType.includes('mpeg')) return 'speech-input.mp4'
  if (mimeType.includes('wav')) return 'speech-input.wav'
  return 'speech-input.webm'
}
