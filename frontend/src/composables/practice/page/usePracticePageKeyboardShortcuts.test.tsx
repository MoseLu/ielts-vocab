import React from 'react'
import { fireEvent, render, screen } from '@testing-library/react'
import { vi } from 'vitest'
import { usePracticePageKeyboardShortcuts } from './usePracticePageKeyboardShortcuts'
import type { PracticeMode } from '../../../components/practice/types'

const openGlobalWordSearchMock = vi.fn()
const dispatchPreviousMock = vi.fn()
const dispatchNextMock = vi.fn()
const dispatchReplayMock = vi.fn()
const playWordMock = vi.fn()
const playExampleAudioMock = vi.fn()
const handleOptionSelectMock = vi.fn()
const handleSkipMock = vi.fn()
const handleGoBackMock = vi.fn()
const handleFavoriteToggleMock = vi.fn()
const onExitHomeMock = vi.fn()

vi.mock('../../../components/layout/navigation/globalWordSearchEvents', () => ({
  openGlobalWordSearch: (...args: unknown[]) => openGlobalWordSearchMock(...args),
}))

vi.mock('../../../components/practice/page/practiceGlobalShortcutEvents', () => ({
  dispatchPracticeGlobalShortcutPrevious: (...args: unknown[]) => dispatchPreviousMock(...args),
  dispatchPracticeGlobalShortcutNext: (...args: unknown[]) => dispatchNextMock(...args),
  dispatchPracticeGlobalShortcutReplay: (...args: unknown[]) => dispatchReplayMock(...args),
}))

vi.mock('../../../components/practice/utils', () => ({
  playExampleAudio: (...args: unknown[]) => playExampleAudioMock(...args),
}))

type HarnessProps = {
  mode?: PracticeMode
}

function ShortcutHarness({ mode = 'listening' }: HarnessProps) {
  usePracticePageKeyboardShortcuts({
    mode,
    smartDimension: 'listening',
    choiceOptionsReady: true,
    showWordList: false,
    showPracticeSettings: false,
    showResult: false,
    spellingResult: null,
    currentWord: {
      word: 'apple',
      phonetic: '/a/',
      pos: 'n.',
      definition: 'fruit',
      examples: [{ en: 'Apple trees grow well here.', zh: '苹果树在这里长得很好。' }],
    },
    optionsLength: 4,
    settings: { playbackSpeed: '1', volume: '100' },
    playWord: playWordMock,
    handleOptionSelect: handleOptionSelectMock,
    handleSkip: handleSkipMock,
    handleGoBack: handleGoBackMock,
    handleFavoriteToggle: handleFavoriteToggleMock,
    onExitHome: onExitHomeMock,
  })

  return (
    <div>
      <button type="button">anchor</button>
      <input aria-label="plain-input" />
      <input aria-label="spelling-input" className="spelling-input" />
    </div>
  )
}

describe('usePracticePageKeyboardShortcuts', () => {
  beforeEach(() => {
    openGlobalWordSearchMock.mockReset()
    dispatchPreviousMock.mockReset()
    dispatchNextMock.mockReset()
    dispatchReplayMock.mockReset()
    playWordMock.mockReset()
    playExampleAudioMock.mockReset()
    handleOptionSelectMock.mockReset()
    handleSkipMock.mockReset()
    handleGoBackMock.mockReset()
    handleFavoriteToggleMock.mockReset()
    onExitHomeMock.mockReset()
  })

  it('opens global search and toggles favorite for shift shortcuts', () => {
    render(<ShortcutHarness />)

    fireEvent.keyDown(window, { key: 'Q', code: 'KeyQ', shiftKey: true })
    fireEvent.keyDown(window, { key: 'W', code: 'KeyW', shiftKey: true })
    fireEvent.keyDown(window, { key: 'ArrowLeft', code: 'ArrowLeft' })
    fireEvent.keyDown(window, { key: 'ArrowRight', code: 'ArrowRight' })

    expect(openGlobalWordSearchMock).toHaveBeenCalledTimes(1)
    expect(handleFavoriteToggleMock).toHaveBeenCalledTimes(1)
    expect(handleGoBackMock).toHaveBeenCalledTimes(1)
    expect(handleSkipMock).toHaveBeenCalledTimes(1)
  })

  it('replays audio when Tab is pressed from the spelling input', () => {
    render(<ShortcutHarness mode="dictation" />)

    fireEvent.keyDown(screen.getByLabelText('spelling-input'), { key: 'Tab', code: 'Tab' })

    expect(playWordMock).toHaveBeenCalledWith('apple')
  })

  it('plays example audio when Alt is pressed in an example-enabled mode', () => {
    render(<ShortcutHarness mode="dictation" />)

    fireEvent.keyDown(screen.getByLabelText('spelling-input'), {
      key: 'Alt',
      code: 'AltLeft',
      altKey: true,
    })

    expect(playExampleAudioMock).toHaveBeenCalledWith(
      'Apple trees grow well here.',
      'apple',
      { playbackSpeed: '1', volume: '100' },
    )
  })

  it('dispatches shared bridge events for quick-memory shortcuts', () => {
    render(<ShortcutHarness mode="quickmemory" />)

    fireEvent.keyDown(window, { key: 'ArrowLeft', code: 'ArrowLeft' })
    fireEvent.keyDown(window, { key: 'ArrowRight', code: 'ArrowRight' })
    fireEvent.keyDown(window, { key: 'Tab', code: 'Tab' })

    expect(dispatchPreviousMock).toHaveBeenCalledTimes(1)
    expect(dispatchNextMock).toHaveBeenCalledTimes(1)
    expect(dispatchReplayMock).toHaveBeenCalledTimes(1)
  })
})
