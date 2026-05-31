import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'
import QuickMemoryMode from './QuickMemoryMode'
import type { AppSettings, Word } from './types'
import { STORAGE_KEYS } from '../../constants'

const apiFetchMock = vi.fn(() => Promise.resolve({}))
const logSessionMock = vi.fn()
const startSessionMock = vi.fn(() => Promise.resolve(1))
const showToastMock = vi.fn()

vi.mock('./utils', () => ({
  playWordAudio: vi.fn(() => Promise.resolve(true)),
  prepareWordAudioPlayback: vi.fn(() => Promise.resolve(true)),
  preloadWordAudio: vi.fn(() => Promise.resolve(true)),
  preloadWordAudioBatch: vi.fn(() => Promise.resolve(true)),
  stopAudio: vi.fn(),
}))

vi.mock('../../hooks/useAIChat', () => ({
  PASSIVE_STUDY_SESSION_MIN_SECONDS: 30,
  prepareStudySessionForLearningAction: undefined,
  finalizeStudySessionSegment: undefined,
  isStudySessionActive: undefined,
  resolveStudySessionDurationSeconds: () => 60,
  logSession: (...args: unknown[]) => logSessionMock(...args),
  startSession: (...args: unknown[]) => startSessionMock(...args),
  cancelSession: vi.fn(() => Promise.resolve()),
  flushStudySessionOnPageHide: vi.fn(),
  touchStudySessionActivity: vi.fn(),
  updateStudySessionSnapshot: vi.fn(),
}))

vi.mock('../../lib', () => ({
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
}))

vi.mock('../../lib/apiClient', () => ({
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
  buildApiUrl: (path: string) => path,
}))

vi.mock('../../contexts/ToastContext', () => ({
  useToast: () => ({ showToast: showToastMock }),
}))

describe('QuickMemoryMode completion', () => {
  const vocabulary: Word[] = [
    { word: 'apple', phonetic: '/apple/', pos: 'n.', definition: 'fruit' },
  ]
  const settings: AppSettings = {}

  beforeEach(() => {
    apiFetchMock.mockClear()
    logSessionMock.mockClear()
    startSessionMock.mockClear()
    showToastMock.mockClear()
    localStorage.clear()
    localStorage.setItem(STORAGE_KEYS.AUTH_USER, JSON.stringify({ id: 1 }))
  })

  it('shows the summary when final session logging is still pending', async () => {
    logSessionMock.mockImplementation(() => new Promise<void>(() => {}))
    const user = userEvent.setup()
    const { container } = render(
      <QuickMemoryMode
        vocabulary={vocabulary}
        queue={[0]}
        settings={settings}
        bookId="book-1"
        chapterId="1"
        bookChapters={[{ id: '1', title: 'Chapter 1' }]}
        onModeChange={() => {}}
        onNavigate={() => {}}
        onWrongWord={() => {}}
      />,
    )

    await user.click(container.querySelector('.qm-btn--known') as HTMLButtonElement)
    await waitFor(() => expect(container.querySelector('.qm-card--reveal')).not.toBeNull())
    await user.click(container.querySelector('.qm-btn-next') as HTMLButtonElement)

    await waitFor(() => {
      expect(screen.getByText('本轮完成')).toBeInTheDocument()
    })
    expect(logSessionMock).toHaveBeenCalled()
  })
})
