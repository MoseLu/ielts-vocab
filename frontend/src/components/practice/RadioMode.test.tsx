import React from 'react'
import { act, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'
import RadioMode from './RadioMode'
import type { RadioModeProps } from './types'
import { playWordAudio } from './utils'
import { PRACTICE_GLOBAL_SHORTCUT_REPLAY_EVENT } from './page/practiceGlobalShortcutEvents'

vi.mock('./utils', () => ({
  playWordAudio: vi.fn(),
  preloadWordAudioBatch: vi.fn(),
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

  it('reports the displayed word index when the user skips forward', async () => {
    const user = userEvent.setup()
    const onIndexChange = vi.fn()

    render(
      <RadioMode
        {...baseProps}
        vocabulary={[
          baseProps.vocabulary[0],
          { word: 'minus', phonetic: '/ˈmaɪnəs/', pos: 'prep.', definition: '减去' },
        ]}
        queue={[0, 1]}
        onIndexChange={onIndexChange}
      />,
    )

    await user.click(screen.getByTitle('下一个'))

    expect(onIndexChange).toHaveBeenNthCalledWith(1, 0)
    expect(onIndexChange).toHaveBeenLastCalledWith(1)
    expect(screen.getByText('minus')).toBeInTheDocument()
  })

  it('replays the current word when the shared replay shortcut event is dispatched', async () => {
    render(<RadioMode {...baseProps} />)

    vi.mocked(playWordAudio).mockClear()
    await act(async () => {
      await Promise.resolve()
      window.dispatchEvent(new Event(PRACTICE_GLOBAL_SHORTCUT_REPLAY_EVENT))
      await Promise.resolve()
    })

    expect(playWordAudio).toHaveBeenCalledWith('plus', baseProps.settings, expect.any(Function))
  })

  it('keeps favorite and speaking actions on opposite sides of the toolbar', () => {
    const { container } = render(
      <RadioMode
        {...baseProps}
        favoriteSlot={<button type="button">fav</button>}
        speakingSlot={<button type="button">speak</button>}
      />,
    )

    expect(container.querySelector('.radio-stage-toolbar__side button')?.textContent).toBe('fav')
    expect(container.querySelector('.radio-stage-toolbar__side--end button')?.textContent).toBe('speak')
  })
})
