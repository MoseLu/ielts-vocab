import { render } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import QuickMemoryMode from './QuickMemoryMode'
import type { AppSettings, Word } from './types'

vi.mock('./utils', () => ({
  playWordAudio: () => Promise.resolve(true),
  prepareWordAudioPlayback: () => Promise.resolve(true),
  preloadWordAudio: () => Promise.resolve(true),
  preloadWordAudioBatch: () => Promise.resolve(true),
  stopAudio: () => {},
}))

vi.mock('../../hooks/useAIChat', () => ({
  PASSIVE_STUDY_SESSION_MIN_SECONDS: 30,
  resolveStudySessionDurationSeconds: (data: { startedAt: number; endedAt?: number; durationSeconds?: number }) =>
    data.durationSeconds ?? Math.max(0, Math.round(((data.endedAt ?? Date.now()) - data.startedAt) / 1000)),
  logSession: () => Promise.resolve(),
  startSession: () => Promise.resolve(1),
  cancelSession: () => Promise.resolve(),
  flushStudySessionOnPageHide: () => {},
  touchStudySessionActivity: () => {},
  updateStudySessionSnapshot: () => {},
}))

vi.mock('../../lib', () => ({
  apiFetch: () => Promise.resolve({}),
}))

vi.mock('../../contexts/ToastContext', () => ({
  useToast: () => ({ showToast: () => {} }),
}))

describe('QuickMemoryMode layout', () => {
  const vocabulary: Word[] = [
    { word: 'apple', phonetic: '/ˈæpəl/', pos: 'n.', definition: 'fruit' },
  ]
  const settings: AppSettings = {}

  beforeEach(() => {
    localStorage.clear()
  })

  it('keeps the progress header and card inside one centered stage container', () => {
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

    const stage = container.querySelector('.qm-stage')
    expect(stage?.querySelector('.qm-progress-track')).not.toBeNull()
    expect(stage?.querySelector('.qm-progress-label')).not.toBeNull()
    expect(stage?.querySelector('.qm-card')).not.toBeNull()
  })
})
