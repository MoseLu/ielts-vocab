import type { MutableRefObject } from 'react'
import type { Socket } from 'socket.io-client'

import {
  buildPcmPayloadFromChunks,
  SPEECH_REALTIME_PCM_BATCH_BYTES,
} from './speechRecognitionUtils'

const REALTIME_GATE_HANGOVER_FRAMES = 4
const REALTIME_GATE_OPEN_FRAMES = 2
const REALTIME_GATE_PREROLL_CHUNKS = 8
const SPEECH_FRAME_ACTIVE_SAMPLE = 280
const SPEECH_FRAME_PEAK = 1100
const SPEECH_FRAME_RMS = 190

export interface BufferedSocketAudioState {
  bytes: number
  chunks: Int16Array[]
  gateOpen: boolean
  hasSpeech: boolean
  preRollChunks: Int16Array[]
  silenceFrames: number
  speechFrames: number
}

function createBufferedSocketAudioState(): BufferedSocketAudioState {
  return {
    bytes: 0,
    chunks: [],
    gateOpen: false,
    hasSpeech: false,
    preRollChunks: [],
    silenceFrames: 0,
    speechFrames: 0,
  }
}

function isSpeechLikePcmFrame(pcmData: Int16Array) {
  let peak = 0
  let sumSquares = 0
  let activeSamples = 0

  for (const sample of pcmData) {
    const magnitude = Math.abs(sample)
    if (magnitude > peak) peak = magnitude
    if (magnitude >= SPEECH_FRAME_ACTIVE_SAMPLE) activeSamples += 1
    sumSquares += sample * sample
  }

  const rms = Math.sqrt(sumSquares / Math.max(1, pcmData.length))
  const activeRatio = activeSamples / Math.max(1, pcmData.length)
  return (
    (peak >= SPEECH_FRAME_PEAK && rms >= SPEECH_FRAME_RMS) ||
    (rms >= 240 && activeRatio >= 0.08) ||
    (peak >= 900 && rms >= 150 && activeRatio >= 0.14)
  )
}

export const detectSpeechLikePcmFrame = isSpeechLikePcmFrame

function enqueueSocketAudio(
  socketRef: MutableRefObject<Socket | null>,
  stateRef: MutableRefObject<BufferedSocketAudioState>,
  pcmData: Int16Array,
) {
  stateRef.current.chunks.push(pcmData)
  stateRef.current.bytes += pcmData.byteLength
  if (stateRef.current.bytes >= SPEECH_REALTIME_PCM_BATCH_BYTES) {
    flushBufferedSocketAudio(socketRef, stateRef)
  }
}

function rememberPreRollChunk(state: BufferedSocketAudioState, pcmData: Int16Array) {
  state.preRollChunks.push(pcmData)
  if (state.preRollChunks.length > REALTIME_GATE_PREROLL_CHUNKS) {
    state.preRollChunks.shift()
  }
}

export function resetBufferedSocketAudio(stateRef: MutableRefObject<BufferedSocketAudioState>) {
  stateRef.current = createBufferedSocketAudioState()
}

export function hasBufferedSocketSpeech(stateRef: MutableRefObject<BufferedSocketAudioState>) {
  return stateRef.current.hasSpeech
}

export function flushBufferedSocketAudio(
  socketRef: MutableRefObject<Socket | null>,
  stateRef: MutableRefObject<BufferedSocketAudioState>,
) {
  if (!stateRef.current.bytes || !socketRef.current?.connected) return
  socketRef.current.emit('audio_data', buildPcmPayloadFromChunks(stateRef.current.chunks))
  resetBufferedSocketAudio(stateRef)
}

export function queueBufferedSocketAudio(
  socketRef: MutableRefObject<Socket | null>,
  stateRef: MutableRefObject<BufferedSocketAudioState>,
  pcmData: Int16Array,
) {
  const state = stateRef.current
  const speechLike = isSpeechLikePcmFrame(pcmData)

  if (!state.gateOpen) {
    rememberPreRollChunk(state, pcmData)
    state.speechFrames = speechLike ? state.speechFrames + 1 : 0
    if (state.speechFrames < REALTIME_GATE_OPEN_FRAMES) return state.hasSpeech

    state.gateOpen = true
    state.hasSpeech = true
    state.silenceFrames = 0
    state.speechFrames = 0
    const pendingChunks = state.preRollChunks
    state.preRollChunks = []
    for (const chunk of pendingChunks) {
      enqueueSocketAudio(socketRef, stateRef, chunk)
    }
    return state.hasSpeech
  }

  if (speechLike) {
    state.silenceFrames = 0
    enqueueSocketAudio(socketRef, stateRef, pcmData)
    return state.hasSpeech
  }

  state.silenceFrames += 1
  if (state.silenceFrames <= REALTIME_GATE_HANGOVER_FRAMES) {
    enqueueSocketAudio(socketRef, stateRef, pcmData)
    return state.hasSpeech
  }

  state.gateOpen = false
  state.silenceFrames = 0
  rememberPreRollChunk(state, pcmData)
  return state.hasSpeech
}
