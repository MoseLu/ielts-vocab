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

  it('uploads browser-recorded audio before the wav pcm fallback', async () => {
    const fetchMock = vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
      const formData = init?.body as FormData
      const audio = formData.get('audio')
      expect(audio).toBeInstanceOf(File)
      expect((audio as File).name).toBe('speech-input.webm')
      expect((audio as File).type).toBe('audio/webm')

      return new Response(JSON.stringify({ text: 'browser blob transcript' }), {
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
    expect(onResult).toHaveBeenCalledWith('browser blob transcript')
    expect(onError).not.toHaveBeenCalled()
    expect(onFinish).toHaveBeenCalledTimes(1)
  })

  it('waits for media recorder data before falling back to pcm upload', () => {
    const setRequestedCaptureId = vi.fn()
    const upload = vi.fn()
    const recorder = {
      state: 'recording',
      requestData: vi.fn(),
      stop: vi.fn(),
    } as unknown as MediaRecorder

    expect(requestRecordedAudioFallback({
      captureId: 11,
      requestedCaptureId: null,
      setRequestedCaptureId,
      recorder,
      chunks: [],
      pcmChunks: [Int16Array.from([1, 2, 3])],
      upload,
    })).toBe(true)

    expect(setRequestedCaptureId).toHaveBeenCalledWith(11)
    expect(recorder.requestData).toHaveBeenCalledTimes(1)
    expect(recorder.stop).toHaveBeenCalledTimes(1)
    expect(upload).not.toHaveBeenCalled()
  })

  it('surfaces a local error instead of uploading oversized fallback audio', async () => {
    const fetchMock = vi.fn()

    Object.defineProperty(globalThis, 'fetch', {
      configurable: true,
      value: fetchMock,
    })

    const onError = vi.fn()
    const onFinish = vi.fn()
    const onResult = vi.fn()

    await uploadRecordedAudio({
      captureId: 12,
      chunks: [new Blob([new Uint8Array(750 * 1024)], { type: 'audio/webm' })],
      mimeType: 'audio/webm',
      pcmChunks: [],
      getCurrentCaptureId: () => 12,
      getCurrentTranscriptSource: () => null,
      onFinish,
      onResult,
      onError,
    })

    expect(fetchMock).not.toHaveBeenCalled()
    expect(onResult).not.toHaveBeenCalled()
    expect(onError).toHaveBeenCalledWith('单次语音过长，请缩短后重试')
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
