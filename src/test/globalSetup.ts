// ── Global Setup: mock browser APIs used across the codebase ───────────────────

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

// Mock speechSynthesis (no vi.fn here — globalSetup runs before test globals)
const speechSynthesisMock = {
  speak: () => {},
  cancel: () => {},
  pause: () => {},
  resume: () => {},
  getVoices: () => [],
  onvoiceschanged: null,
  pending: false,
  speaking: false,
  paused: false,
}
Object.defineProperty(globalThis, 'speechSynthesis', { value: speechSynthesisMock, writable: true })

// Mock Audio
class MockAudio {
  play = () => Promise.resolve()
  pause = () => {}
  onended: (() => void) | null = null
  onerror: (() => void) | null = null
  volume = 1
  playbackRate = 1
  currentTime = 0
  duration = 0
  src = ''
  load = () => {}
  canPlayType = () => ''
}
Object.defineProperty(globalThis, 'Audio', { value: MockAudio as unknown as typeof Audio, writable: true })

// Mock fetch
Object.defineProperty(globalThis, 'fetch', {
  value: () => Promise.resolve(new Response()),
  writable: true,
  configurable: true,
})

export default async () => {
  // Reset global state before each test file runs
  localStorage.clear()
}
