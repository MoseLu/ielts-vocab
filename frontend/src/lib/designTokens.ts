export const DESIGN_TOKEN_BREAKPOINTS = {
  phone: 375,
  phoneLg: 480,
  tabletSm: 640,
  tablet: 768,
  desktop: 1024,
  wide: 1280,
  ultra: 1440,
} as const

export const DESIGN_TOKEN_SIZES = {
  1: 1,
  2: 2,
  4: 4,
  6: 6,
  8: 8,
  10: 10,
  12: 12,
  14: 14,
  16: 16,
  18: 18,
  20: 20,
  24: 24,
  28: 28,
  32: 32,
  36: 36,
  40: 40,
  44: 44,
  48: 48,
  56: 56,
  64: 64,
  72: 72,
  80: 80,
  96: 96,
  120: 120,
  320: 320,
} as const

export const DESIGN_TOKEN_KEYS = {
  waveformActiveBar: '--waveform-bar-active',
  waveformActiveDot: '--waveform-dot-active',
  waveformIdleBar: '--waveform-bar-idle',
  waveformIdleDot: '--waveform-dot-idle',
  waveformBarWidth: '--waveform-bar-width',
  waveformBarGap: '--waveform-bar-gap',
} as const

type DesignTokenKey = typeof DESIGN_TOKEN_KEYS[keyof typeof DESIGN_TOKEN_KEYS] | `--${string}`

function getComputedRootStyle() {
  if (typeof window === 'undefined') return null
  return window.getComputedStyle(document.documentElement)
}

export function readCssToken(token: DesignTokenKey, fallback = ''): string {
  const styles = getComputedRootStyle()
  const value = styles?.getPropertyValue(token).trim()
  return value || fallback
}

export function readCssPxToken(token: DesignTokenKey, fallback: number): number {
  const raw = readCssToken(token)
  const parsed = Number.parseFloat(raw)
  return Number.isFinite(parsed) ? parsed : fallback
}

export function buildMinWidthMediaQuery(width: number): string {
  return `(min-width: ${width}px)`
}
