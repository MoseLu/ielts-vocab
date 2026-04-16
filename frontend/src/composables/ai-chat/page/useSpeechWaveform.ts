import { useCallback, useEffect, useRef } from 'react'
import {
  DESIGN_TOKEN_KEYS,
  DESIGN_TOKEN_SIZES,
  readCssPxToken,
  readCssToken,
} from '../../../lib/designTokens'

const DEFAULT_WAVEFORM_CONFIG = {
  barWidth: DESIGN_TOKEN_SIZES[2],
  gap: DESIGN_TOKEN_SIZES[1],
  holdFrames: 3,
  maxBars: 420,
  maxHeightRatio: 0.46,
  minSpeechHalfHeight: 1.2,
  noiseFloorFollowQuiet: 0.22,
  noiseFloorFollowSpeech: 0.05,
  speechCloseThreshold: 0.07,
  speechOpenThreshold: 0.11,
  visibleThreshold: 0.018,
}

const DEFAULT_WAVEFORM_THEME = {
  activeBarColor: 'rgba(38, 46, 58, 0.96)',
  activeDotColor: 'rgba(38, 46, 58, 0.18)',
  idleBarColor: 'rgba(96, 104, 118, 0.76)',
  idleDotColor: 'rgba(96, 104, 118, 0.14)',
}

interface WaveformProcessorState {
  adaptiveFloor: number
  adaptivePeak: number
  lastNormalized: number
  lastVisual: number
  recentActive: number[]
  recentLevels: number[]
  speechActive: boolean
  speechHoldFrames: number
}

function createProcessorState(): WaveformProcessorState {
  return {
    adaptiveFloor: 0.0025,
    adaptivePeak: 0.06,
    lastNormalized: 0,
    lastVisual: 0,
    recentActive: [],
    recentLevels: [],
    speechActive: false,
    speechHoldFrames: 0,
  }
}

function clamp01(value: number) {
  return Math.min(1, Math.max(0, value))
}

function getPercentile(levels: number[], percentile: number) {
  if (!levels.length) return 0
  const sorted = [...levels].sort((left, right) => left - right)
  const boundedPercentile = clamp01(percentile)
  const index = Math.min(
    sorted.length - 1,
    Math.max(0, Math.floor((sorted.length - 1) * boundedPercentile)),
  )
  return sorted[index] ?? 0
}

function setupHiDPICanvas(canvas: HTMLCanvasElement) {
  const rect = canvas.getBoundingClientRect()
  const width = Math.max(1, Math.round(rect.width))
  const height = Math.max(1, Math.round(rect.height))
  const dpr = window.devicePixelRatio || 1
  const scaledWidth = Math.round(width * dpr)
  const scaledHeight = Math.round(height * dpr)

  if (canvas.width !== scaledWidth || canvas.height !== scaledHeight) {
    canvas.width = scaledWidth
    canvas.height = scaledHeight
  }

  let ctx: CanvasRenderingContext2D | null = null
  try {
    ctx = canvas.getContext('2d')
  } catch {
    return null
  }
  if (!ctx) return null

  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  return { ctx, height, width }
}

export function useSpeechWaveform() {
  const canvasNodeRef = useRef<HTMLCanvasElement | null>(null)
  const historyRef = useRef<number[]>([])
  const isRecordingRef = useRef(false)
  const processorStateRef = useRef<WaveformProcessorState>(createProcessorState())
  const resizeObserverRef = useRef<ResizeObserver | null>(null)
  const renderFrameRef = useRef<number | null>(null)

  const drawWaveform = useCallback(() => {
    const canvas = canvasNodeRef.current
    if (!canvas) return

    const setup = setupHiDPICanvas(canvas)
    if (!setup) return

    const { ctx, height, width } = setup
    const barWidth = readCssPxToken(DESIGN_TOKEN_KEYS.waveformBarWidth, DEFAULT_WAVEFORM_CONFIG.barWidth)
    const gap = readCssPxToken(DESIGN_TOKEN_KEYS.waveformBarGap, DEFAULT_WAVEFORM_CONFIG.gap)
    const activeDotColor = readCssToken(DESIGN_TOKEN_KEYS.waveformActiveDot, DEFAULT_WAVEFORM_THEME.activeDotColor)
    const activeBarColor = readCssToken(DESIGN_TOKEN_KEYS.waveformActiveBar, DEFAULT_WAVEFORM_THEME.activeBarColor)
    const idleDotColor = readCssToken(DESIGN_TOKEN_KEYS.waveformIdleDot, DEFAULT_WAVEFORM_THEME.idleDotColor)
    const idleBarColor = readCssToken(DESIGN_TOKEN_KEYS.waveformIdleBar, DEFAULT_WAVEFORM_THEME.idleBarColor)
    const stride = barWidth + gap
    const count = Math.max(1, Math.floor(width / stride))
    const history = historyRef.current
    const midlineY = Math.round(height / 2)
    const maxHalfHeight = height * DEFAULT_WAVEFORM_CONFIG.maxHeightRatio
    const dotColor = isRecordingRef.current
      ? activeDotColor
      : idleDotColor
    const barColor = isRecordingRef.current
      ? activeBarColor
      : idleBarColor

    ctx.clearRect(0, 0, width, height)
    ctx.fillStyle = dotColor
    for (let column = 0; column < count; column += 1) {
      const x = column * stride + barWidth / 2
      ctx.beginPath()
      ctx.arc(x, midlineY, 0.8, 0, Math.PI * 2)
      ctx.fill()
    }

    ctx.fillStyle = barColor
    for (let column = 0; column < count; column += 1) {
      const historyIndex = history.length - count + column
      const amplitude = historyIndex >= 0 ? history[historyIndex] ?? 0 : 0
      if (amplitude < DEFAULT_WAVEFORM_CONFIG.visibleThreshold) continue

      const halfHeight = DEFAULT_WAVEFORM_CONFIG.minSpeechHalfHeight + amplitude * maxHalfHeight
      const x = column * stride
      const y = midlineY - halfHeight
      const barHeight = halfHeight * 2

      ctx.beginPath()
      if (typeof ctx.roundRect === 'function') {
        ctx.roundRect(x, y, barWidth, barHeight, barWidth / 2)
      } else {
        ctx.rect(x, y, barWidth, barHeight)
      }
      ctx.fill()
    }
  }, [])

  const requestDraw = useCallback(() => {
    if (renderFrameRef.current !== null) return
    renderFrameRef.current = window.requestAnimationFrame(() => {
      renderFrameRef.current = null
      drawWaveform()
    })
  }, [drawWaveform])

  const disconnectResizeObserver = useCallback(() => {
    resizeObserverRef.current?.disconnect()
    resizeObserverRef.current = null
  }, [])

  const attachCanvas = useCallback((node: HTMLCanvasElement | null) => {
    disconnectResizeObserver()
    canvasNodeRef.current = node
    if (!node) return

    if (typeof ResizeObserver === 'function') {
      const observer = new ResizeObserver(() => requestDraw())
      observer.observe(node)
      resizeObserverRef.current = observer
    }

    requestDraw()
  }, [disconnectResizeObserver, requestDraw])

  const calculateVisualAmplitude = useCallback((rawAmplitude: number) => {
    const state = processorStateRef.current
    const raw = clamp01(rawAmplitude)
    const floorRate = raw <= state.adaptiveFloor * 1.18
      ? DEFAULT_WAVEFORM_CONFIG.noiseFloorFollowQuiet
      : DEFAULT_WAVEFORM_CONFIG.noiseFloorFollowSpeech
    state.adaptiveFloor += (raw - state.adaptiveFloor) * floorRate

    const gate = Math.max(0.02, state.adaptiveFloor * 1.34 + 0.004)
    const gated = Math.max(0, raw - gate)
    state.recentLevels.push(gated)
    if (state.recentLevels.length > 8) {
      state.recentLevels.shift()
    }
    if (gated > 0.003) {
      state.recentActive.push(gated)
      if (state.recentActive.length > 32) {
        state.recentActive.shift()
      }
    }

    const localPeak = Math.max(
      0.05,
      getPercentile(state.recentLevels, 0.75),
      getPercentile(state.recentActive, 0.82),
    )
    const peakFollow = localPeak >= state.adaptivePeak ? 0.24 : 0.08
    state.adaptivePeak += (localPeak - state.adaptivePeak) * peakFollow

    const normalized = gated <= 0
      ? 0
      : clamp01(gated / Math.max(0.028, state.adaptivePeak))

    if (normalized >= DEFAULT_WAVEFORM_CONFIG.speechOpenThreshold) {
      state.speechActive = true
      state.speechHoldFrames = DEFAULT_WAVEFORM_CONFIG.holdFrames
    } else if (state.speechActive) {
      if (normalized >= DEFAULT_WAVEFORM_CONFIG.speechCloseThreshold) {
        state.speechHoldFrames = DEFAULT_WAVEFORM_CONFIG.holdFrames
      } else if (state.speechHoldFrames > 0) {
        state.speechHoldFrames -= 1
      } else {
        state.speechActive = false
      }
    }

    if (!state.speechActive && normalized <= DEFAULT_WAVEFORM_CONFIG.speechCloseThreshold) {
      state.lastNormalized = normalized
      state.lastVisual *= 0.36
      if (state.lastVisual < DEFAULT_WAVEFORM_CONFIG.visibleThreshold) {
        state.lastVisual = 0
      }
      return state.lastVisual
    }

    const contrast = Math.abs(normalized - state.lastNormalized)
    const target = clamp01(Math.pow(normalized, 0.82) * 0.86 + contrast * 0.16)
    state.lastVisual = target >= state.lastVisual
      ? target * 0.76 + state.lastVisual * 0.24
      : target * 0.44 + state.lastVisual * 0.56
    state.lastNormalized = normalized

    if (state.lastVisual < DEFAULT_WAVEFORM_CONFIG.visibleThreshold) {
      state.lastVisual = 0
    }
    return state.lastVisual
  }, [])

  const pushAmplitude = useCallback((rawAmplitude: number) => {
    historyRef.current.push(calculateVisualAmplitude(rawAmplitude))
    if (historyRef.current.length > DEFAULT_WAVEFORM_CONFIG.maxBars) {
      historyRef.current.shift()
    }
    requestDraw()
  }, [calculateVisualAmplitude, requestDraw])

  const resetWaveform = useCallback(() => {
    historyRef.current = []
    processorStateRef.current = createProcessorState()
    requestDraw()
  }, [requestDraw])

  const setWaveformRecordingState = useCallback((isRecording: boolean) => {
    isRecordingRef.current = isRecording
    requestDraw()
  }, [requestDraw])

  useEffect(() => () => {
    if (renderFrameRef.current !== null) {
      window.cancelAnimationFrame(renderFrameRef.current)
      renderFrameRef.current = null
    }
    disconnectResizeObserver()
  }, [disconnectResizeObserver])

  return {
    attachCanvas,
    pushAmplitude,
    resetWaveform,
    setWaveformRecordingState,
  }
}
