import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  requestRecordedAudioFallback,
  uploadRecordedAudio,
} from './speechRecognitionFileFallback'

describe('speechRecognitionFileFallback', () => {
  const originalFetch = globalThis.fetch

  afterEach(() => {
    Object.defineProperty(globalThis, 'fetch', {
      configurable: true,
      value: originalFetch,
    })
  })

  it('uploads a wav built from pcm chunks before browser-recorded blobs', async () => {
    const fetchMock = vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
      const formData = init?.body as FormData
      const audio = formData.get('audio')
      expect(audio).toBeInstanceOf(File)
      expect((audio as File).name).toBe('speech-input.wav')
      expect((audio as File).type).toBe('audio/wav')

      return new Response(JSON.stringify({ text: 'wav fallback transcript' }), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      })
    })

    Object.defineProperty(globalThis, 'fetch', {
      configurable: true,
      value: fetchMock,
    })

    const onError = vi.fn()
    const onFinish = vi.fn()
    const onResult = vi.fn()

    await uploadRecordedAudio({
      captureId: 7,
      chunks: [new Blob(['webm-bytes'], { type: 'audio/webm' })],
      mimeType: 'audio/webm',
      pcmChunks: [Int16Array.from([0, 800, -900, 400])],
      getCurrentCaptureId: () => 7,
      getCurrentTranscriptSource: () => null,
      onFinish,
      onResult,
      onError,
    })

    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(onResult).toHaveBeenCalledWith('wav fallback transcript')
    expect(onError).not.toHaveBeenCalled()
    expect(onFinish).toHaveBeenCalledTimes(1)
  })

  it('requests upload immediately when pcm fallback audio is already available', () => {
    const setRequestedCaptureId = vi.fn()
    const upload = vi.fn()

    expect(requestRecordedAudioFallback({
      captureId: 9,
      requestedCaptureId: null,
      setRequestedCaptureId,
      recorder: null,
      chunks: [],
      pcmChunks: [Int16Array.from([1, 2, 3])],
      upload,
    })).toBe(true)

    expect(setRequestedCaptureId).toHaveBeenCalledWith(9)
    expect(upload).toHaveBeenCalledWith(9)
  })
})
