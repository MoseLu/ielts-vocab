import { consumeManagedAudioFailureReason } from './utils.audio.failure'
import {
  __resetManagedAudioStateForTests,
  getManagedAudioLeadInMs,
  playManagedAudioBuffer,
  playManagedAudioUrl,
  prepareManagedAudioBuffer,
  prepareManagedAudioUrl,
  stopManagedAudio,
  warmupManagedAudio,
} from './utils.audio.playback'
import {
  __resetPracticeAudioResourceStateForTests,
  invalidateWordAudioUrlCache,
  resolvePracticeAudioAsset,
  resolveWordAudioAsset,
} from './practiceAudio.resources'
import type {
  PracticeAudioListener,
  PracticeAudioPlaySettings,
  PracticeAudioRequest,
  PracticeAudioRequestContext,
  PracticeAudioSnapshot,
  PreparedAudioAsset,
  PreparedAudioClip,
  WordAudioRequest,
} from './practiceAudio.types'

const IDLE_SNAPSHOT: PracticeAudioSnapshot = {
  state: 'idle',
  requestId: null,
  origin: null,
  wordKey: null,
  queueIndex: null,
  autoplay: false,
  assetId: null,
  clipIndex: -1,
  clipCount: 0,
  currentTimeMs: 0,
  durationMs: null,
  error: null,
}

function readVolume(settings: PracticeAudioPlaySettings): number {
  const parsed = Number.parseFloat(String(settings.volume ?? '100')) / 100
  if (!Number.isFinite(parsed)) return 1
  return Math.min(1, Math.max(0, parsed))
}

function readPlaybackRate(settings: PracticeAudioPlaySettings): number {
  const parsed = Number.parseFloat(String(settings.playbackSpeed ?? '1'))
  if (!Number.isFinite(parsed)) return 1
  return Math.min(4, Math.max(0.25, parsed))
}

class PracticeAudioSession {
  private listeners = new Set<PracticeAudioListener>()
  private snapshot: PracticeAudioSnapshot = IDLE_SNAPSHOT
  private generation = 0
  private requestSequence = 0
  private progressFrame: number | null = null
  private lastPlayback:
    | {
        request: PracticeAudioRequest
        context: Required<PracticeAudioRequestContext>
        settings: PracticeAudioPlaySettings
        onEnd?: () => void
      }
    | null = null

  getSnapshot(): PracticeAudioSnapshot {
    return this.snapshot
  }

  subscribe(listener: PracticeAudioListener): () => void {
    this.listeners.add(listener)
    listener(this.snapshot)
    return () => {
      this.listeners.delete(listener)
    }
  }

  stop(): void {
    this.generation += 1
    this.clearProgress()
    stopManagedAudio()
    this.publish(IDLE_SNAPSHOT)
  }

  async prepare(request: PracticeAudioRequest, options?: { forceMetadataCheck?: boolean }): Promise<boolean> {
    const asset = await resolvePracticeAudioAsset(request, options)
    if (!asset) return false
    return this.prepareAsset(asset)
  }

  async preload(
    requests: PracticeAudioRequest[],
    options?: { forceMetadataCheck?: boolean },
  ): Promise<void> {
    await Promise.allSettled(requests.map(request => this.prepare(request, options)))
  }

  async replay(): Promise<boolean> {
    if (!this.lastPlayback) return false
    const { request, context, settings, onEnd } = this.lastPlayback
    return this.play(request, settings, context, { onEnd })
  }

  async play(
    request: PracticeAudioRequest,
    settings: PracticeAudioPlaySettings,
    context: PracticeAudioRequestContext,
    options?: { forceMetadataCheck?: boolean; onEnd?: () => void },
  ): Promise<boolean> {
    const playbackContext = this.resolveContext(request, context)
    const generation = ++this.generation
    this.clearProgress()
    stopManagedAudio()
    this.publish({
      state: 'preparing',
      requestId: playbackContext.requestId,
      origin: playbackContext.origin,
      wordKey: playbackContext.wordKey,
      queueIndex: playbackContext.queueIndex,
      autoplay: playbackContext.autoplay,
      assetId: null,
      clipIndex: -1,
      clipCount: 0,
      currentTimeMs: 0,
      durationMs: null,
      error: null,
    })
    const asset = await resolvePracticeAudioAsset(request, options)
    if (!this.isCurrent(generation)) return false
    if (!asset) {
      this.publish({ ...this.snapshot, state: 'error', error: 'audio-missing' })
      options?.onEnd?.()
      return false
    }
    this.lastPlayback = { request, context: playbackContext, settings, onEnd: options?.onEnd }
    return this.playClip(asset, 0, generation, playbackContext, settings, options?.onEnd)
  }

  private resolveContext(
    request: PracticeAudioRequest,
    context: PracticeAudioRequestContext,
  ): Required<PracticeAudioRequestContext> {
    return {
      requestId: context.requestId ?? `${context.origin}:${++this.requestSequence}`,
      origin: context.origin,
      wordKey: context.wordKey ?? this.resolveWordKey(request),
      queueIndex: context.queueIndex ?? null,
      autoplay: Boolean(context.autoplay),
    }
  }

  private resolveWordKey(request: PracticeAudioRequest): string | null {
    if (request.kind === 'word') return request.word.trim().toLowerCase() || null
    if (request.kind === 'example') return request.word.trim().toLowerCase() || null
    return request.payload.word.trim().toLowerCase() || null
  }

  private async prepareAsset(asset: PreparedAudioAsset): Promise<boolean> {
    const results = await Promise.allSettled(asset.clips.map(clip => this.prepareClip(clip)))
    return results.some(result => result.status === 'fulfilled' && result.value)
  }

  private async prepareClip(clip: PreparedAudioClip): Promise<boolean> {
    const [prepared] = await Promise.all([
      clip.buffer
        ? prepareManagedAudioBuffer(clip.buffer)
        : clip.fallbackUrl
          ? prepareManagedAudioUrl(clip.fallbackUrl)
          : Promise.resolve(false),
      warmupManagedAudio(),
    ])
    if (prepared) return true
    if (!clip.fallbackUrl || clip.buffer == null) return false
    return prepareManagedAudioUrl(clip.fallbackUrl)
  }

  private async playClip(
    asset: PreparedAudioAsset,
    clipIndex: number,
    generation: number,
    context: Required<PracticeAudioRequestContext>,
    settings: PracticeAudioPlaySettings,
    onEnd?: () => void,
  ): Promise<boolean> {
    const clip = asset.clips[clipIndex]
    if (!clip) {
      this.finishPlayback(generation, context, asset, clipIndex - 1, onEnd)
      return false
    }
    const playbackRate = asset.kind === 'follow-sequence'
      ? clip.playbackRate
      : readPlaybackRate(settings) * clip.playbackRate
    const playbackOptions = {
      isCurrent: () => this.isCurrent(generation),
      isStopped: () => !this.isCurrent(generation),
      volume: readVolume(settings),
      rate: playbackRate,
      onEnd: () => {
        if (!this.isCurrent(generation)) return
        this.clearProgress()
        if (clipIndex + 1 < asset.clips.length) {
          void this.playClip(asset, clipIndex + 1, generation, context, settings, onEnd)
          return
        }
        this.finishPlayback(generation, context, asset, clipIndex, onEnd)
      },
    }
    this.publish({
      state: 'playing',
      requestId: context.requestId,
      origin: context.origin,
      wordKey: context.wordKey,
      queueIndex: context.queueIndex,
      autoplay: context.autoplay,
      assetId: asset.assetId,
      clipIndex,
      clipCount: asset.clips.length,
      currentTimeMs: 0,
      durationMs: clip.durationMs,
      error: null,
    })
    this.startProgress(generation, asset, clipIndex, context)
    let started = await this.playPreparedClip(clip, playbackOptions)
    const failureReason = consumeManagedAudioFailureReason()
    if (!started && asset.kind === 'word' && (asset.request as WordAudioRequest).sourcePreference === 'url' && failureReason !== 'not-allowed') {
      const fallbackAsset = await resolveWordAudioAsset({
        kind: 'word',
        word: (asset.request as WordAudioRequest).word,
        sourcePreference: 'buffer',
      })
      if (!this.isCurrent(generation) || !fallbackAsset) return false
      started = await this.playClip(fallbackAsset, clipIndex, generation, context, settings, onEnd)
      return started
    }
    if (started || !this.isCurrent(generation)) return started
    if (failureReason === 'not-allowed') {
      this.publish({ ...this.snapshot, state: 'blocked', error: null })
      return false
    }
    this.publish({ ...this.snapshot, state: 'error', error: 'audio-playback-failed' })
    onEnd?.()
    return false
  }

  private async playPreparedClip(
    clip: PreparedAudioClip,
    options: Parameters<typeof playManagedAudioBuffer>[1],
  ): Promise<boolean> {
    if (clip.buffer) {
      const startedFromBuffer = await playManagedAudioBuffer(clip.buffer, options)
      if (startedFromBuffer || consumeManagedAudioFailureReason() === 'not-allowed') return startedFromBuffer
    }
    if (!clip.fallbackUrl) return false
    return playManagedAudioUrl(clip.fallbackUrl, options)
  }

  private startProgress(
    generation: number,
    asset: PreparedAudioAsset,
    clipIndex: number,
    context: Required<PracticeAudioRequestContext>,
  ): void {
    const clip = asset.clips[clipIndex]
    if (!clip?.trackTimeline || !clip.durationMs || typeof window === 'undefined') return
    const startedAt = performance.now()
    const leadInMs = getManagedAudioLeadInMs()
    const tick = () => {
      if (!this.isCurrent(generation)) return
      const elapsedMs = Math.max(0, performance.now() - startedAt - leadInMs)
      const nextTimeMs = Math.min(clip.durationMs ?? elapsedMs, elapsedMs)
      this.publish({
        state: 'playing',
        requestId: context.requestId,
        origin: context.origin,
        wordKey: context.wordKey,
        queueIndex: context.queueIndex,
        autoplay: context.autoplay,
        assetId: asset.assetId,
        clipIndex,
        clipCount: asset.clips.length,
        currentTimeMs: nextTimeMs,
        durationMs: clip.durationMs,
        error: null,
      })
      if (nextTimeMs < (clip.durationMs ?? nextTimeMs)) {
        this.progressFrame = window.requestAnimationFrame(tick)
      }
    }
    this.progressFrame = window.requestAnimationFrame(tick)
  }

  private finishPlayback(
    generation: number,
    context: Required<PracticeAudioRequestContext>,
    asset: PreparedAudioAsset,
    clipIndex: number,
    onEnd?: () => void,
  ): void {
    if (!this.isCurrent(generation)) return
    this.publish({
      state: 'ended',
      requestId: context.requestId,
      origin: context.origin,
      wordKey: context.wordKey,
      queueIndex: context.queueIndex,
      autoplay: context.autoplay,
      assetId: asset.assetId,
      clipIndex,
      clipCount: asset.clips.length,
      currentTimeMs: this.snapshot.durationMs ?? this.snapshot.currentTimeMs,
      durationMs: this.snapshot.durationMs,
      error: null,
    })
    onEnd?.()
  }

  private isCurrent(generation: number): boolean {
    return this.generation === generation
  }

  private clearProgress(): void {
    if (this.progressFrame == null || typeof window === 'undefined') return
    window.cancelAnimationFrame(this.progressFrame)
    this.progressFrame = null
  }

  private publish(snapshot: PracticeAudioSnapshot): void {
    this.snapshot = snapshot
    for (const listener of this.listeners) listener(snapshot)
  }

  resetForTests(): void {
    this.listeners.clear()
    this.lastPlayback = null
    this.requestSequence = 0
    this.generation = 0
    this.clearProgress()
    stopManagedAudio()
    __resetPracticeAudioResourceStateForTests()
    __resetManagedAudioStateForTests()
    this.snapshot = IDLE_SNAPSHOT
  }
}

export const practiceAudioSession = new PracticeAudioSession()

export function getPracticeAudioSnapshot(): PracticeAudioSnapshot {
  return practiceAudioSession.getSnapshot()
}

export function subscribePracticeAudio(listener: PracticeAudioListener): () => void {
  return practiceAudioSession.subscribe(listener)
}

export function stopPracticeAudio(): void {
  practiceAudioSession.stop()
}

export async function preparePracticeAudio(
  request: PracticeAudioRequest,
  options?: { forceMetadataCheck?: boolean },
): Promise<boolean> {
  return practiceAudioSession.prepare(request, options)
}

export async function preloadPracticeAudio(
  requests: PracticeAudioRequest[],
  options?: { forceMetadataCheck?: boolean },
): Promise<void> {
  return practiceAudioSession.preload(requests, options)
}

export async function playPracticeAudio(
  request: PracticeAudioRequest,
  settings: PracticeAudioPlaySettings,
  context: PracticeAudioRequestContext,
  options?: { forceMetadataCheck?: boolean; onEnd?: () => void },
): Promise<boolean> {
  return practiceAudioSession.play(request, settings, context, options)
}

export async function replayPracticeAudio(): Promise<boolean> {
  return practiceAudioSession.replay()
}

export function __resetPracticeAudioSessionForTests(): void {
  practiceAudioSession.resetForTests()
}

export { invalidateWordAudioUrlCache }
