import { encodePcm16, normalizeAudioLevel } from './speechRecognitionUtils'

const MIC_CAPTURE_WORKLET_URL = new URL('../worklets/micCaptureProcessor.js', import.meta.url)

export interface SpeechAudioCaptureSession {
  stop: () => Promise<void>
}

interface StartSpeechAudioCaptureOptions {
  stream: MediaStream
  onLevel: (level: number) => void
  onPcmFrame: (pcmData: Int16Array) => void
}

function disconnectNode(node: AudioNode | MediaStreamAudioSourceNode | null | undefined) {
  if (!node) return
  try {
    node.disconnect()
  } catch {}
}

async function createAudioWorkletCapture(
  audioContext: AudioContext,
  source: MediaStreamAudioSourceNode,
  onAudioFrame: (inputData: Float32Array, sampleRate: number) => void,
) {
  if (!audioContext.audioWorklet || typeof AudioWorkletNode !== 'function') return null

  try {
    await audioContext.audioWorklet.addModule(MIC_CAPTURE_WORKLET_URL.toString())
    const sink = audioContext.createGain()
    sink.gain.value = 0
    const workletNode = new AudioWorkletNode(audioContext, 'speech-mic-capture', {
      channelCount: 1,
      channelCountMode: 'explicit',
      numberOfInputs: 1,
      numberOfOutputs: 1,
      outputChannelCount: [1],
    })

    workletNode.port.onmessage = event => {
      const inputData = event.data instanceof Float32Array
        ? event.data
        : event.data instanceof ArrayBuffer
          ? new Float32Array(event.data)
          : null
      if (!inputData?.length) return
      onAudioFrame(inputData, audioContext.sampleRate)
    }

    source.connect(workletNode)
    workletNode.connect(sink)
    sink.connect(audioContext.destination)

    return async () => {
      workletNode.port.onmessage = null
      disconnectNode(source)
      disconnectNode(workletNode)
      disconnectNode(sink)
      await audioContext.close().catch(() => {})
    }
  } catch {
    return null
  }
}

function createScriptProcessorCapture(
  audioContext: AudioContext,
  source: MediaStreamAudioSourceNode,
  onAudioFrame: (inputData: Float32Array, sampleRate: number) => void,
) {
  const processor = audioContext.createScriptProcessor(4096, 1, 1)
  const sink = audioContext.createGain()
  sink.gain.value = 0

  processor.onaudioprocess = event => {
    onAudioFrame(event.inputBuffer.getChannelData(0), audioContext.sampleRate)
  }

  source.connect(processor)
  processor.connect(sink)
  sink.connect(audioContext.destination)

  return async () => {
    processor.onaudioprocess = null
    disconnectNode(source)
    disconnectNode(processor)
    disconnectNode(sink)
    await audioContext.close().catch(() => {})
  }
}

export async function startSpeechAudioCapture({
  stream,
  onLevel,
  onPcmFrame,
}: StartSpeechAudioCaptureOptions): Promise<SpeechAudioCaptureSession> {
  const audioContext = new AudioContext()
  if (audioContext.state === 'suspended') {
    await audioContext.resume()
  }

  const source = audioContext.createMediaStreamSource(stream)
  const handleAudioFrame = (inputData: Float32Array, sampleRate: number) => {
    onLevel(normalizeAudioLevel(inputData))
    onPcmFrame(encodePcm16(inputData, sampleRate))
  }

  const stop = await createAudioWorkletCapture(audioContext, source, handleAudioFrame)
    ?? createScriptProcessorCapture(audioContext, source, handleAudioFrame)

  return { stop }
}
