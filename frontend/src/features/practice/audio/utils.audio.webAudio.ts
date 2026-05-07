type ManagedAudioKeepAliveSource = {
  connect: (destinationNode: AudioNode) => unknown
  disconnect: () => unknown
  start: (when?: number) => void
  stop: (when?: number) => void
}

export type ManagedAudioKeepAliveState = {
  source: ManagedAudioKeepAliveSource | null
  gain: GainNode | null
}

const MIN_WEB_AUDIO_START_DELAY_S = 0.05
const MAX_WEB_AUDIO_START_DELAY_S = 0.12
const DEFAULT_WEB_AUDIO_LEADING_SILENCE_S = 0.24
const MAX_WEB_AUDIO_LEADING_SILENCE_S = 0.42
const WEB_AUDIO_WARMUP_FLOOR = 0.00035
const WEB_AUDIO_KEEP_ALIVE_GAIN = 0.00002

function clampNumber(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value))
}

function readManagedAudioLatency(audioContext: AudioContext): number {
  const latencyContext = audioContext as AudioContext & { outputLatency?: number }
  const baseLatency = Number.isFinite(audioContext.baseLatency) ? audioContext.baseLatency : 0
  const outputLatency = Number.isFinite(latencyContext.outputLatency) ? latencyContext.outputLatency ?? 0 : 0
  return Math.max(0, baseLatency + outputLatency)
}

export function getManagedAudioStartDelaySeconds(audioContext: AudioContext): number {
  return clampNumber(
    MIN_WEB_AUDIO_START_DELAY_S + readManagedAudioLatency(audioContext),
    MIN_WEB_AUDIO_START_DELAY_S,
    MAX_WEB_AUDIO_START_DELAY_S,
  )
}

export function getManagedAudioLeadingSilenceSeconds(audioContext: AudioContext): number {
  return clampNumber(
    DEFAULT_WEB_AUDIO_LEADING_SILENCE_S + readManagedAudioLatency(audioContext),
    DEFAULT_WEB_AUDIO_LEADING_SILENCE_S,
    MAX_WEB_AUDIO_LEADING_SILENCE_S,
  )
}

export function stopManagedAudioKeepAlive(state: ManagedAudioKeepAliveState): void {
  if (state.source) {
    try { state.source.stop(0) } catch {}
    try { state.source.disconnect() } catch {}
    state.source = null
  }
  if (state.gain) {
    try { state.gain.disconnect() } catch {}
    state.gain = null
  }
}

export function fillManagedAudioLeadIn(channelData: Float32Array, leadingFrames: number, channelIndex: number): void {
  for (let frame = 0; frame < leadingFrames; frame += 1) {
    const pseudoNoise = (((frame * 17 + channelIndex * 31) % 23) - 11) / 11
    channelData[frame] = pseudoNoise * WEB_AUDIO_WARMUP_FLOOR
  }
}

export function ensureManagedAudioKeepAlive(audioContext: AudioContext, state: ManagedAudioKeepAliveState): void {
  if (state.source || audioContext.state !== 'running') return
  try {
    const gainNode = audioContext.createGain()
    gainNode.gain.value = WEB_AUDIO_KEEP_ALIVE_GAIN
    const keepAliveContext = audioContext as AudioContext & { createConstantSource?: () => ConstantSourceNode }
    const keepAliveSource = typeof keepAliveContext.createConstantSource === 'function'
      ? keepAliveContext.createConstantSource()
      : (() => {
          const source = audioContext.createBufferSource()
          const buffer = audioContext.createBuffer(1, Math.max(128, Math.round(audioContext.sampleRate * 0.02)), audioContext.sampleRate)
          fillManagedAudioLeadIn(buffer.getChannelData(0), buffer.length, 0)
          source.buffer = buffer
          source.loop = true
          return source
        })()
    keepAliveSource.connect(gainNode)
    gainNode.connect(audioContext.destination)
    keepAliveSource.start(audioContext.currentTime)
    state.source = keepAliveSource as ManagedAudioKeepAliveSource
    state.gain = gainNode
  } catch {
    stopManagedAudioKeepAlive(state)
  }
}

export function getManagedAudioLeadInMs(audioContext: AudioContext | null | undefined): number {
  const startDelaySeconds = audioContext
    ? getManagedAudioStartDelaySeconds(audioContext)
    : MIN_WEB_AUDIO_START_DELAY_S
  const leadingSilenceSeconds = audioContext
    ? getManagedAudioLeadingSilenceSeconds(audioContext)
    : DEFAULT_WEB_AUDIO_LEADING_SILENCE_S
  return Math.round((startDelaySeconds + leadingSilenceSeconds) * 1000)
}
