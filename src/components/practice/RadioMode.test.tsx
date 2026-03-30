import React from 'react'
import { render, screen } from '@testing-library/react'
import { vi } from 'vitest'
import RadioMode from './RadioMode'
import type { RadioModeProps } from './types'

vi.mock('./utils', () => ({
  playWordAudio: vi.fn(),
  stopAudio: vi.fn(),
  syllabifyWord: (word: string) => [word],
}))

describe('RadioMode layout', () => {
  const baseProps: RadioModeProps = {
    vocabulary: [
      {
        word: 'plus',
        phonetic: '/plʌs/',
        pos: 'prep.',
        definition: '加上',
      },
    ],
    queue: [0],
    radioIndex: 0,
    showSettings: false,
    settings: {
      playbackCount: '1',
      interval: '2',
      loopMode: false,
    },
    onRadioSkipPrev: vi.fn(),
    onRadioSkipNext: vi.fn(),
    onRadioPause: vi.fn(),
    onRadioResume: vi.fn(),
    onRadioRestart: vi.fn(),
    onRadioStop: vi.fn(),
    onNavigate: vi.fn(),
    onCloseSettings: vi.fn(),
    onModeChange: vi.fn(),
  }

  it('shows word, phonetic and definition without hover', () => {
    const { container } = render(<RadioMode {...baseProps} />)

    expect(screen.getByText('plus')).toBeInTheDocument()
    expect(screen.getByText('/plʌs/')).toBeInTheDocument()
    expect(screen.getByText('加上')).toBeInTheDocument()
    expect(screen.getByText('1 / 1')).toBeInTheDocument()
    expect(screen.queryByText('★ ★ ★')).not.toBeInTheDocument()
    expect(container.querySelector('.radio-stage-line')).toBeNull()
  })
})
