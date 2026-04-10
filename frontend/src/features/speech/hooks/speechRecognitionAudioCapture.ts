import { encodePcm16, normalizeAudioLevel } from './speechRecognitionUtils'

const MIC_CAPTURE_WORKLET_URL = new URL('../worklets/micCaptureProcessor.js', import.meta.url)
const PCM_LEVEL_EMIT_INTERVAL_MS = 36
const PCM_LEVEL_WINDOW_SIZE = 64

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

function resolveAudioContextClass() {
  return window.AudioContext
    ?? (window as Window & typeof globalThis & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext
}

function collectPcmWindowLevels(inputData: Float32Array) {
  const windows: number[] = []

  for (let start = 0; start < inputData.length; start += PCM_LEVEL_WINDOW_SIZE) {
    const end = Math.min(start + PCM_LEVEL_WINDOW_SIZE, inputData.length)
    let sum = 0
    let sumSquares = 0
    let peak = 0

    for (let index = start; index < end; index += 1) {
      const magnitude = Math.abs(inputData[index])
      peak = Math.max(peak, magnitude)
      sum += magnitude
      sumSquares += magnitude * magnitude
    }

    const sampleCount = Math.max(1, end - start)
    const mean = sum / sampleCount
    const rms = Math.sqrt(sumSquares / sampleCount)
    windows.push(rms * 0.82 + peak * 0.18 + mean * 0.04)
  }

  return windows
}

function applyAdaptiveSpeechGain(inputData: Float32Array) {
  if (!inputData.length) return inputData

  let peak = 0
  let sumSquares = 0

  for (let index = 0; index < inputData.length; index += 1) {
    const sample = inputData[index]
    const magnitude = Math.abs(sample)
    peak = Math.max(peak, magnitude)
    sumSquares += sample * sample
  }

  const rms = Math.sqrt(sumSquares / inputData.length)
  const looksLikeSilence = peak < 0.012 && rms < 0.004
  if (looksLikeSilence) {
    return inputData
  }

  const targetPeak = peak < 0.035 ? 0.34 : peak < 0.07 ? 0.26 : 0.18
  const targetRms = rms < 0.015 ? 0.11 : rms < 0.03 ? 0.09 : 0.07
  const peakGain = targetPeak / Math.max(0.012, peak)
  const rmsGain = targetRms / Math.max(0.005, rms)
  const gain = Math.min(6.4, Math.max(1, Math.min(peakGain, rmsGain)))

  if (gain <= 1.02) {
    return inputData
  }

  const outputData = new Float32Array(inputData.length)
  const softClipFactor = 1.06

  for (let index = 0; index < inputData.length; index += 1) {
    const amplified = inputData[index] * gain
    outputData[index] = Math.tanh(amplified * softClipFactor) / softClipFactor
  }

  return outputData
}

function createPcmLevelMonitor(onLevel: (level: number) => void) {
  let pendingDurationMs = 0
  let pendingWindows: number[] = []
  let ambientFloor = 0.0024
  let activeCeiling = 0.028
  let lastLevel = 0

  return {
    push(inputData: Float32Array, sampleRate: number) {
      if (!inputData.length || !sampleRate) return

      pendingDurationMs += inputData.length / sampleRate * 1000
      pendingWindows.push(...collectPcmWindowLevels(inputData))

      while (pendingDurationMs >= PCM_LEVEL_EMIT_INTERVAL_MS) {
        if (!pendingWindows.length) {
          onLevel(0)
          pendingDurationMs -= PCM_LEVEL_EMIT_INTERVAL_MS
          continue
        }

        const sorted = [...pendingWindows].sort((left, right) => left - right)
        const peak = sorted[sorted.length - 1] ?? 0
        const floor = sorted[0] ?? ambientFloor
        const upperMedian = sorted[Math.min(sorted.length - 1, Math.floor(sorted.length * 0.72))] ?? 0
        let motion = 0

        for (let index = 1; index < pendingWindows.length; index += 1) {
          const diff = pendingWindows[index] - pendingWindows[index - 1]
          motion += Math.abs(diff)
        }

        motion /= Math.max(1, pendingWindows.length - 1)
        const energy = upperMedian * 0.82 + peak * 0.18
        const floorFollow = energy <= ambientFloor * 1.24 ? 0.24 : 0.035
        ambientFloor += (energy - ambientFloor) * floorFollow

        const gate = Math.max(0.0034, ambientFloor * 1.28 + 0.0014)
        const spread = Math.max(0, peak - floor)
        const gated = Math.max(0, energy - gate)
        const looksLikeNoise =
          peak < 0.014 &&
          upperMedian < 0.009 &&
          motion < 0.0032 &&
          spread < 0.006

        if (looksLikeNoise || gated <= 0.0018) {
          lastLevel *= 0.42
          if (lastLevel < 0.012) {
            lastLevel = 0
          }
          onLevel(lastLevel)
          pendingWindows = []
          pendingDurationMs -= PCM_LEVEL_EMIT_INTERVAL_MS
          continue
        }

        const ceilingTarget = Math.max(0.024, gated, upperMedian - ambientFloor)
        const ceilingFollow = ceilingTarget >= activeCeiling ? 0.28 : 0.08
        activeCeiling += (ceilingTarget - activeCeiling) * ceilingFollow

        const normalized = Math.min(1, Math.max(0, gated / Math.max(0.02, activeCeiling)))
        const dynamicAccent = Math.min(0.22, motion * 8.5 + spread * 3.2)
        const shaped = Math.pow(normalized, 0.82) * 0.84 + dynamicAccent
        lastLevel = shaped >= lastLevel
          ? shaped * 0.78 + lastLevel * 0.22
          : shaped * 0.48 + lastLevel * 0.52

        onLevel(lastLevel < 0.03 ? 0 : Math.min(1, lastLevel))
        pendingWindows = []
        pendingDurationMs -= PCM_LEVEL_EMIT_INTERVAL_MS
      }
    },
    flush() {
      pendingDurationMs = 0
      pendingWindows = []
      ambientFloor = 0.0024
      activeCeiling = 0.028
      lastLevel = 0
    },
  }
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
  const processor = audioContext.createScriptProcessor(1024, 1, 1)
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
  const AudioContextClass = resolveAudioContextClass()
  if (!AudioContextClass) {
    throw new Error('当前环境不支持 Web Audio API')
  }

  const audioContext = new AudioContextClass()
  if (audioContext.state === 'suspended') {
    await audioContext.resume()
  }

  const source = audioContext.createMediaStreamSource(stream)
  const pcmLevelMonitor = createPcmLevelMonitor(onLevel)
  const handleAudioFrame = (inputData: Float32Array, sampleRate: number) => {
    pcmLevelMonitor.push(inputData, sampleRate)
    if (!audioContext.audioWorklet && typeof audioContext.createAnalyser !== 'function') {
      onLevel(normalizeAudioLevel(inputData))
    }
    onPcmFrame(encodePcm16(applyAdaptiveSpeechGain(inputData), sampleRate))
  }

  const stop = await createAudioWorkletCapture(audioContext, source, handleAudioFrame)
    ?? createScriptProcessorCapture(audioContext, source, handleAudioFrame)

  return {
    stop: async () => {
      pcmLevelMonitor.flush()
      await stop()
    },
  }
}
