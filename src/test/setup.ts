// ── Test Setup: extends vitest globals with @testing-library/jest-dom ─────────
import '@testing-library/jest-dom'
import { vi } from 'vitest'

// ── Mock browser APIs used across the codebase ───────────────────────────────

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {}
  return {
    getItem: (key: string) => store[key] ?? null,
    setItem: (key: string, value: string) => { store[key] = value },
    removeItem: (key: string) => { delete store[key] },
    clear: () => { store = {} },
    get length() { return Object.keys(store).length },
    key: (i: number) => Object.keys(store)[i] ?? null,
  }
})()
Object.defineProperty(globalThis, 'localStorage', { value: localStorageMock, writable: true })

// Mock sessionStorage
const sessionStorageMock = (() => {
  let store: Record<string, string> = {}
  return {
    getItem: (key: string) => store[key] ?? null,
    setItem: (key: string, value: string) => { store[key] = value },
    removeItem: (key: string) => { delete store[key] },
    clear: () => { store = {} },
    get length() { return Object.keys(store).length },
    key: (i: number) => Object.keys(store)[i] ?? null,
  }
})()
Object.defineProperty(globalThis, 'sessionStorage', { value: sessionStorageMock, writable: true })

// Mock speechSynthesis
const speechSynthesisMock = {
  speak: vi.fn(),
  cancel: vi.fn(),
  pause: vi.fn(),
  resume: vi.fn(),
  getVoices: vi.fn(() => []),
  onvoiceschanged: null,
  addEventListener: vi.fn(),
  removeEventListener: vi.fn(),
  dispatchEvent: vi.fn(() => true),
  pending: false,
  speaking: false,
  paused: false,
}
Object.defineProperty(globalThis, 'speechSynthesis', { value: speechSynthesisMock, writable: true })

// Mock Audio
class MockAudio {
  play = vi.fn().mockResolvedValue(undefined)
  pause = vi.fn()
  onended: (() => void) | null = null
  onerror: (() => void) | null = null
  volume = 1
  playbackRate = 1
  currentTime = 0
  duration = 0
  src = ''
  load = vi.fn()
  canPlayType = vi.fn(() => '')
}
Object.defineProperty(globalThis, 'Audio', { value: MockAudio as unknown as typeof Audio, writable: true })

// Mock fetch
Object.defineProperty(globalThis, 'fetch', {
  value: vi.fn(() => Promise.resolve(new Response())),
  writable: true,
  configurable: true,
})
