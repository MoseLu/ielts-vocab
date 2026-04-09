import type { MutableRefObject } from 'react'
import type { Socket } from 'socket.io-client'

import {
  buildPcmPayloadFromChunks,
  SPEECH_REALTIME_PCM_BATCH_BYTES,
} from './speechRecognitionUtils'

export interface BufferedSocketAudioState {
  bytes: number
  chunks: Int16Array[]
}

export function resetBufferedSocketAudio(stateRef: MutableRefObject<BufferedSocketAudioState>) {
  stateRef.current = { bytes: 0, chunks: [] }
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
  stateRef.current.chunks.push(pcmData)
  stateRef.current.bytes += pcmData.byteLength
  if (stateRef.current.bytes >= SPEECH_REALTIME_PCM_BATCH_BYTES) {
    flushBufferedSocketAudio(socketRef, stateRef)
  }
}
