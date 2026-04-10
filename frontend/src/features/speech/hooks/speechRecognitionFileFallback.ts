import { buildApiUrl } from '../../../lib'
import {
  buildWavBlobFromPcmChunks,
  buildRecordedAudioFilename,
  resolveMediaRecorderMimeType,
  SPEECH_EMPTY_RESULT_MESSAGE,
} from './speechRecognitionUtils'

const SPEECH_WAV_FALLBACK_MAX_BYTES = 900 * 1024
const SPEECH_UPLOAD_SAFE_MAX_BYTES = 700 * 1024
const SPEECH_UPLOAD_TOO_LARGE_MESSAGE = '单次语音过长，请缩短后重试'

export interface StartedMediaRecorderCapture {
  mimeType: string
  recorder: MediaRecorder
}

interface UploadRecordedAudioOptions {
  captureId: number
  chunks: Blob[]
  mimeType: string
  pcmChunks: Int16Array[]
  getCurrentCaptureId: () => number
  getCurrentTranscriptSource: () => string | null
  getDeferredTranscript?: () => string
  onFinish: () => void
  onDeferredTranscript?: (text: string) => void
  onResult: (text: string) => void
  onError: (message: string) => void
}

interface RequestRecordedAudioFallbackOptions {
  captureId: number
  requestedCaptureId: number | null
  setRequestedCaptureId: (captureId: number) => void
  recorder: MediaRecorder | null
  chunks: Blob[]
  pcmChunks: Int16Array[]
  upload: (captureId: number) => void
}

interface UploadAudioAttempt {
  audioBlob: Blob
  filename: string
}

async function transcribeRecordedAudio(audioBlob: Blob, filename: string) {
  const formData = new FormData()
  formData.append('audio', audioBlob, filename)

  const response = await fetch(buildApiUrl('/api/speech/transcribe'), {
    method: 'POST',
    body: formData,
    credentials: 'include',
    signal: AbortSignal.timeout(45_000),
  })
  const payload = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new Error(
      typeof payload.error === 'string' && payload.error.trim()
        ? payload.error.trim()
        : response.status === 413
          ? '单次语音过长，请缩短后重试'
        : '语音转写失败，请重试'
    )
  }

  return typeof payload.text === 'string' ? payload.text.trim() : ''
}

export async function uploadRecordedAudio({
  captureId,
  chunks,
  mimeType,
  pcmChunks,
  getCurrentCaptureId,
  getCurrentTranscriptSource,
  getDeferredTranscript,
  onFinish,
  onDeferredTranscript,
  onResult,
  onError,
}: UploadRecordedAudioOptions) {
  if (captureId !== getCurrentCaptureId() || getCurrentTranscriptSource()) return

  const audioChunks = chunks.filter(chunk => chunk.size > 0)
  const uploadAttempts: UploadAudioAttempt[] = []

  if (pcmChunks.some(chunk => chunk.length > 0)) {
    const wavBlob = buildWavBlobFromPcmChunks(pcmChunks)
    if (!audioChunks.length || wavBlob.size <= SPEECH_WAV_FALLBACK_MAX_BYTES) {
      uploadAttempts.push({
        audioBlob: wavBlob,
        filename: 'speech-input.wav',
      })
    }
  }

  if (audioChunks.length) {
    const audioBlob = new Blob(audioChunks, { type: mimeType || 'audio/webm' })
    uploadAttempts.push({
      audioBlob,
      filename: buildRecordedAudioFilename(audioBlob.type),
    })
  }

  if (!uploadAttempts.length) {
    const deferredTranscript = getDeferredTranscript?.().trim()
    if (deferredTranscript) {
      onDeferredTranscript?.(deferredTranscript)
    } else {
      onError(SPEECH_EMPTY_RESULT_MESSAGE)
    }
    onFinish()
    return
  }

  try {
    let lastError: string | null = null
    for (const attempt of uploadAttempts) {
      if (attempt.audioBlob.size > SPEECH_UPLOAD_SAFE_MAX_BYTES) {
        lastError = SPEECH_UPLOAD_TOO_LARGE_MESSAGE
        continue
      }
      try {
        const text = await transcribeRecordedAudio(attempt.audioBlob, attempt.filename)
        if (captureId !== getCurrentCaptureId() || getCurrentTranscriptSource()) return
        if (text) {
          onResult(text)
          onFinish()
          return
        }
        lastError = SPEECH_EMPTY_RESULT_MESSAGE
      } catch (error: unknown) {
        lastError =
          error instanceof Error && error.message.trim()
            ? error.message
            : '语音转写失败，请重试'
      }
    }

    const deferredTranscript = getDeferredTranscript?.().trim()
    if (deferredTranscript) {
      onDeferredTranscript?.(deferredTranscript)
    } else {
      onError(lastError ?? SPEECH_EMPTY_RESULT_MESSAGE)
    }
  } catch (error: unknown) {
    if (captureId !== getCurrentCaptureId() || getCurrentTranscriptSource()) return
    const deferredTranscript = getDeferredTranscript?.().trim()
    if (deferredTranscript) {
      onDeferredTranscript?.(deferredTranscript)
    } else {
      onError(
        error instanceof Error && error.message.trim()
          ? error.message
          : '语音转写失败，请重试'
      )
    }
  }

  onFinish()
}

export function requestRecordedAudioFallback({
  captureId,
  requestedCaptureId,
  setRequestedCaptureId,
  recorder,
  chunks,
  pcmChunks,
  upload,
}: RequestRecordedAudioFallbackOptions) {
  if (requestedCaptureId === captureId) return true

  if (recorder && recorder.state !== 'inactive') {
    setRequestedCaptureId(captureId)
    if (typeof recorder.requestData === 'function') {
      try {
        recorder.requestData()
      } catch {}
    }
    try {
      recorder.stop()
      return true
    } catch {}
  }

  if (chunks.some(chunk => chunk.size > 0)) {
    setRequestedCaptureId(captureId)
    upload(captureId)
    return true
  }

  if (pcmChunks.some(chunk => chunk.length > 0)) {
    setRequestedCaptureId(captureId)
    upload(captureId)
    return true
  }

  return false
}

export function startMediaRecorderCapture(
  windowObject: Window & typeof globalThis,
  stream: MediaStream,
  captureId: number,
  onChunk: (chunk: Blob) => void,
  onStop: (captureId: number, recorder: MediaRecorder) => void,
): StartedMediaRecorderCapture | null {
  if (typeof windowObject.MediaRecorder !== 'function') return null

  const preferredMimeType = resolveMediaRecorderMimeType(windowObject)
  const recorder = preferredMimeType
    ? new MediaRecorder(stream, { mimeType: preferredMimeType })
    : new MediaRecorder(stream)

  recorder.ondataavailable = event => {
    if (event.data && event.data.size > 0) {
      onChunk(event.data)
    }
  }
  recorder.onstop = () => {
    onStop(captureId, recorder)
  }
  recorder.start(250)

  return {
    mimeType: recorder.mimeType || preferredMimeType,
    recorder,
  }
}
