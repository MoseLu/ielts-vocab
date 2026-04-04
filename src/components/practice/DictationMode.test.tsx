import React from 'react'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
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
    queueIndex: 1,
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

    expect(screen.getByText('先听例句，再补全空缺词')).toBeInTheDocument()

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

    expect(screen.getByText('先听发音，再完整拼出单词')).toBeInTheDocument()
    expect(onPlayWord).toHaveBeenCalledWith('attention')
  })

  it('reveals the answer after three manual replays', async () => {
    const user = userEvent.setup()
    const onPlayWord = vi.fn()
    const { container } = render(
      <DictationMode {...baseProps} onPlayWord={onPlayWord} />,
    )

    const wordModeButton = container.querySelector('.submode-btn') as HTMLButtonElement
    await user.click(wordModeButton)

    const playButton = container.querySelector('.play-btn-large') as HTMLButtonElement

    expect(container.textContent).toContain('可重复播放，手动播放 3 次后显示答案')
    expect(container.textContent).not.toContain('正确答案：attention')

    await user.click(playButton)
    expect(container.textContent).toContain('已手动播放 1/3 次，再点 2 次显示答案')
    expect(container.textContent).not.toContain('正确答案：attention')

    await user.click(playButton)
    expect(container.textContent).toContain('已手动播放 2/3 次，再点 1 次显示答案')
    expect(container.textContent).not.toContain('正确答案：attention')

    await user.click(playButton)

    expect(onPlayWord).toHaveBeenCalledTimes(3)
    expect(container.textContent).toContain('已显示答案，可直接输入后提交')
    expect(container.textContent).toContain('正确答案')
    expect(container.textContent).toContain('attention')
  })

  it('shows dedicated error feedback UI when spelling is wrong', () => {
    render(
      <DictationMode
        {...baseProps}
        spellingInput="attension"
        spellingResult="wrong"
      />,
    )

    expect(screen.getByText('拼写错误')).toBeInTheDocument()
    expect(screen.getByText('正确拼写')).toBeInTheDocument()
    expect(screen.getByText('你的输入')).toBeInTheDocument()
    expect(screen.getByText('attention')).toBeInTheDocument()
    expect(screen.getByText('attension')).toBeInTheDocument()
    expect(screen.getByText('红色字块是出错位置，空心圈表示漏写。')).toBeInTheDocument()
    expect(screen.getByText('系统正在重播例句，稍后重新填写。')).toBeInTheDocument()
  })

  it('renders a placeholder chip for missing letters in the submitted answer', () => {
    const { container } = render(
      <DictationMode
        {...baseProps}
        spellingInput="attntion"
        spellingResult="wrong"
      />,
    )

    expect(container.querySelector('.dictation-error-word-submitted .dictation-error-letter.is-missing')?.textContent).toBe('○')
    expect(container.querySelector('.dictation-error-word-correct .dictation-error-letter.is-focus')).not.toBeNull()
  })

  it('ignores repeated Enter keydown events while the key is held', () => {
    const onSpellingSubmit = vi.fn()
    render(
      <DictationMode
        {...baseProps}
        onSpellingSubmit={onSpellingSubmit}
      />,
    )

    const input = screen.getByPlaceholderText('输入空缺的单词...')

    fireEvent.keyDown(input, { key: 'Enter', code: 'Enter', repeat: true })
    expect(onSpellingSubmit).not.toHaveBeenCalled()

    fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' })
    expect(onSpellingSubmit).toHaveBeenCalledWith('enter')
    expect(onSpellingSubmit).toHaveBeenCalledTimes(1)
  })
})
