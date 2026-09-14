import React from 'react'
import { render } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'

import PracticePage from './PracticePage'
import { STORAGE_KEYS } from '../../constants'

export const apiFetchMock = vi.fn()
export const startSessionMock = vi.fn().mockResolvedValue(null)
export const fetchMock = vi.fn()
export const useAIChatMock = vi.fn(() => ({
  sendMessage: vi.fn(),
  openPanel: vi.fn(),
  closePanel: vi.fn(),
}))

vi.stubGlobal('fetch', fetchMock)

vi.mock('../../hooks', async () => {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const actual = await vi.importActual<any>('../../hooks')
  return {
    ...actual,
    useAIChat: () => useAIChatMock(),
    useSpeechRecognition: () => ({
    isConnected: false,
    isRecording: false,
    startRecording: vi.fn(),
    stopRecording: vi.fn(),
  })
  }
})

vi.mock('../../lib', async () => {
  const actual = await vi.importActual<typeof import('../../lib')>('../../lib')
  return {
    ...actual,
    apiFetch: (...args: unknown[]) => apiFetchMock(...args),
    buildApiUrl: (path: string) => path,
  }
})

vi.mock('./PracticeControlBar', () => ({
  default: ({ vocabularyLength }: { vocabularyLength?: number }) => (
    <div data-testid="practice-control-bar">total:{vocabularyLength ?? 0}</div>
  ),
}))

vi.mock('./WordListPanel', () => ({
  default: () => null,
}))

vi.mock('./RadioMode', () => ({
  default: () => null,
}))

vi.mock('./DictationMode', () => ({
  default: () => null,
}))

vi.mock('../settings/SettingsPanel', () => ({
  default: () => null,
}))

vi.mock('../ui/Loading', () => ({
  Loading: ({ text }: { text: string }) => <div>{text}</div>,
  PageSkeleton: () => <div data-testid="page-skeleton" />,
}))

export function setAuthenticatedUser(id: number | string) {
  localStorage.setItem(STORAGE_KEYS.AUTH_USER, JSON.stringify({ id }))
}

export function renderPracticePage({
  initialEntries = ['/practice'],
  props = {},
}: {
  initialEntries?: string[]
  props?: Partial<React.ComponentProps<typeof PracticePage>>
} = {}) {
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <PracticePage
        user={{ id: 42 }}
        currentDay={1}
        mode="quickmemory"
        showToast={() => {}}
        onModeChange={() => {}}
        onDayChange={() => {}}
        {...props}
      />
    </MemoryRouter>,
  )
}
