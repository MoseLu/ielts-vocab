import React from 'react'
import { render, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'
import DictationMode from './DictationMode'

const playExampleAudioMock = vi.fn()
const stopAudioMock = vi.fn()

vi.mock('./utils', () => ({
  playExampleAudio: (...args: unknown[]) => playExampleAudioMock(...args),
  stopAudio: (...args: unknown[]) => stopAudioMock(...args),
}))

describe('DictationMode', () => {
  const baseProps = {
    currentWord: {
      word: 'attention',
      phonetic: '/əˈten.ʃən/',
      pos: 'n.',
      definition: 'notice',
      examples: [{ en: 'Pay attention to the main idea.', zh: '注意主旨。' }],
    },
    spellingInput: '',
    spellingResult: null,
    speechConnected: true,
    speechRecording: false,
    settings: { playbackSpeed: '0.8', volume: '100' },
    progressValue: 0.2,
    total: 10,
    previousWord: null,
    lastState: null,
    onSpellingInputChange: vi.fn(),
    onSpellingSubmit: vi.fn(),
    onSkip: vi.fn(),
    onGoBack: vi.fn(),
    onStartRecording: vi.fn(),
    onStopRecording: vi.fn(),
    onPlayWord: vi.fn(),
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('auto-plays example audio when example mode is active', async () => {
    render(<DictationMode {...baseProps} />)

    await waitFor(() => {
      expect(playExampleAudioMock).toHaveBeenCalledWith(
        'Pay attention to the main idea.',
        'attention',
        baseProps.settings,
      )
    })
  })

  it('plays word audio after switching to word dictation mode', async () => {
    const user = userEvent.setup()
    const onPlayWord = vi.fn()
    const { container } = render(
      <DictationMode {...baseProps} onPlayWord={onPlayWord} />,
    )

    const wordModeButton = container.querySelector('.submode-btn') as HTMLButtonElement
    await user.click(wordModeButton)
    await user.click(container.querySelector('.play-btn-large') as HTMLButtonElement)

    expect(onPlayWord).toHaveBeenCalledWith('attention')
  })
})
