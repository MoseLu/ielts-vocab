import React from 'react'
import { render } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'
import PracticePage from './PracticePage'

vi.mock('../../hooks/useSpeechRecognition', () => ({
  useSpeechRecognition: () => ({
    isConnected: true,
    isRecording: false,
    startRecording: vi.fn(),
    stopRecording: vi.fn(),
  }),
}))

describe('PracticePage layout', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders a single layout root with a page skeleton while loading', () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(
      () => new Promise(() => {}) as Promise<Response>,
    )

    const { container } = render(
      <MemoryRouter>
        <PracticePage
          currentDay={1}
          mode="listening"
          onModeChange={() => {}}
          onDayChange={() => {}}
        />
      </MemoryRouter>,
    )

    expect(container.firstElementChild).toHaveClass('practice-session-layout')
    expect(container.querySelector('.page-skeleton--practice')).not.toBeNull()
    expect(container.querySelector('.loading-state')).toBeNull()
  })
})
