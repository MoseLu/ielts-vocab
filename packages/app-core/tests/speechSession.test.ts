import assert from 'node:assert/strict'
import { describe, it } from 'node:test'
import { initialSpeechSessionState, reduceSpeechSession } from '../src'

describe('speech session reducer', () => {
  it('tracks recording, partial result, final result, and reset', () => {
    const recording = reduceSpeechSession(initialSpeechSessionState, {
      type: 'start_recording',
      recognitionId: 7,
    })
    const partial = reduceSpeechSession(recording, { type: 'partial', text: 'hel' })
    const processing = reduceSpeechSession(partial, { type: 'stop_recording' })
    const final = reduceSpeechSession(processing, { type: 'final', text: 'hello' })

    assert.equal(recording.status, 'recording')
    assert.equal(partial.partialText, 'hel')
    assert.equal(processing.status, 'processing')
    assert.deepEqual(
      { finalText: final.finalText, status: final.status },
      { finalText: 'hello', status: 'completed' },
    )
    assert.deepEqual(reduceSpeechSession(final, { type: 'reset' }), initialSpeechSessionState)
  })

  it('clamps native audio levels', () => {
    const high = reduceSpeechSession(initialSpeechSessionState, { type: 'level', level: 2 })
    const low = reduceSpeechSession(high, { type: 'level', level: -1 })

    assert.equal(high.level, 1)
    assert.equal(low.level, 0)
  })

  it('keeps the recording state while the socket finishes connecting', () => {
    const recording = reduceSpeechSession(initialSpeechSessionState, {
      type: 'start_recording',
      recognitionId: 9,
    })
    const connecting = reduceSpeechSession(recording, { type: 'connect' })
    const ready = reduceSpeechSession(connecting, { type: 'ready' })

    assert.equal(connecting.status, 'recording')
    assert.equal(ready.status, 'recording')
  })

  it('keeps recording stoppable when transcription fails mid-capture', () => {
    const recording = reduceSpeechSession(initialSpeechSessionState, {
      type: 'start_recording',
      recognitionId: 10,
    })
    const failed = reduceSpeechSession(recording, { type: 'error', message: 'socket unavailable' })

    assert.equal(failed.status, 'recording')
    assert.equal(failed.error, 'socket unavailable')
  })
})
