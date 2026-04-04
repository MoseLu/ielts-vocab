import React from 'react'
import { act, render } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import AIChatPanel from './AIChatPanel'

const useAIChatMock = vi.fn()
const useSpeechRecognitionMock = vi.fn()
let latestSpeechOptions:
  | {
    onResult?: (text: string) => void
    onPartial?: (text: string) => void
    onError?: (error: string) => void
  }
  | null = null

vi.mock('../hooks/useAIChat', () => ({
  useAIChat: () => useAIChatMock(),
}))

vi.mock('../hooks/useSpeechRecognition', () => ({
  useSpeechRecognition: (options: {
    onResult?: (text: string) => void
    onPartial?: (text: string) => void
    onError?: (error: string) => void
  }) => {
    latestSpeechOptions = options
    return useSpeechRecognitionMock(options)
  },
}))

vi.mock('./ui/Scrollbar', () => ({
  Scrollbar: ({
    children,
    className,
  }: {
    children: React.ReactNode
    className?: string
  }) => (
    <div className={className}>
      <div className="el-scrollbar__wrap">{children}</div>
    </div>
  ),
}))

describe('AIChatPanel', () => {
  beforeEach(() => {
    latestSpeechOptions = null
    useAIChatMock.mockReturnValue({
      messages: [
        {
          id: 'assistant-1',
          role: 'assistant',
          content: '# Study Plan\n- Review confusing phrases\n- Try one contrast quiz',
          timestamp: Date.now(),
        },
      ],
      isLoading: false,
      isGreeting: false,
      greetingDone: true,
      isOpen: true,
      contextLoaded: true,
      openPanel: vi.fn(),
      closePanel: vi.fn(),
      sendMessage: vi.fn(),
    })
    useSpeechRecognitionMock.mockReturnValue({
      isConnected: true,
      isRecording: false,
      isReady: false,
      startRecording: vi.fn().mockResolvedValue(undefined),
      stopRecording: vi.fn(),
    })

    Object.defineProperty(window.HTMLElement.prototype, 'scrollIntoView', {
      configurable: true,
      value: vi.fn(),
    })
    Object.defineProperty(window.HTMLElement.prototype, 'scrollTo', {
      configurable: true,
      value: vi.fn(),
    })
  })

  it('renders assistant markdown and marks assistant bubbles as full width', () => {
    const { container } = render(<AIChatPanel />)

    expect(container.querySelector('.ai-markdown-content h1')?.textContent).toBe('Study Plan')
    expect(container.querySelectorAll('.ai-markdown-content li')).toHaveLength(2)
    expect(container.querySelector('.ai-msg-assistant.ai-msg--assistant-wide')).not.toBeNull()
    expect(container.querySelector('.ai-assistant-bubble')).not.toBeNull()
  })

  it('supports fullscreen toggle', async () => {
    const user = userEvent.setup()
    const { container } = render(<AIChatPanel />)

    const toggleButton = container.querySelector('.ai-panel-icon-btn') as HTMLButtonElement
    expect(toggleButton).not.toBeNull()

    await user.click(toggleButton)
    expect(container.querySelector('.ai-panel.ai-panel--fullscreen')).not.toBeNull()

    await user.click(toggleButton)
    expect(container.querySelector('.ai-panel.ai-panel--fullscreen')).toBeNull()
  })

  it('uses a compact input placeholder in the default panel', () => {
    const { getByPlaceholderText } = render(<AIChatPanel />)

    expect(getByPlaceholderText('输入问题，或发送学习指令')).toBeInTheDocument()
  })

  it('uses semantic quick actions instead of exposing templates', async () => {
    const user = userEvent.setup()
    const sendMessage = vi.fn()
    useAIChatMock.mockReturnValue({
      messages: [
        {
          id: 'assistant-1',
          role: 'assistant',
          content: '你可以直接开始口语训练。',
          timestamp: Date.now(),
        },
      ],
      isLoading: false,
      isGreeting: false,
      greetingDone: true,
      isOpen: true,
      contextLoaded: true,
      openPanel: vi.fn(),
      closePanel: vi.fn(),
      sendMessage,
    })

    const { getByRole, queryByRole } = render(<AIChatPanel />)
    await user.click(getByRole('button', { name: '发音训练' }))

    expect(sendMessage).toHaveBeenCalledWith('开始发音训练')
    expect(queryByRole('button', { name: '口语回答模板' })).toBeNull()
    expect(queryByRole('button', { name: '发音记录模板' })).toBeNull()
  })

  it('marks streaming assistant replies and scrolls the message wrap directly', () => {
    const scrollTo = vi.fn()
    Object.defineProperty(window.HTMLElement.prototype, 'scrollTo', {
      configurable: true,
      value: scrollTo,
    })

    useAIChatMock.mockReturnValue({
      messages: [
        {
          id: 'assistant-streaming',
          role: 'assistant',
          content: 'AI 正在分析你的学习记录',
          isStreaming: true,
          timestamp: Date.now(),
        },
      ],
      isLoading: true,
      isGreeting: false,
      greetingDone: true,
      isOpen: true,
      contextLoaded: true,
      openPanel: vi.fn(),
      closePanel: vi.fn(),
      sendMessage: vi.fn(),
    })

    const { container } = render(<AIChatPanel />)

    expect(container.querySelector('.ai-assistant-bubble--streaming')).not.toBeNull()
    expect(container.querySelector('.ai-assistant-bubble__content--streaming')).not.toBeNull()
    expect(scrollTo).toHaveBeenCalled()
  })

  it('starts voice input and auto-sends the final transcript when the composer is empty', async () => {
    const user = userEvent.setup()
    const startRecording = vi.fn().mockResolvedValue(undefined)
    const sendMessage = vi.fn()

    useAIChatMock.mockReturnValue({
      messages: [],
      isLoading: false,
      isGreeting: false,
      greetingDone: true,
      isOpen: true,
      contextLoaded: true,
      openPanel: vi.fn(),
      closePanel: vi.fn(),
      sendMessage,
    })
    useSpeechRecognitionMock.mockReturnValue({
      isConnected: true,
      isRecording: false,
      isReady: false,
      startRecording,
      stopRecording: vi.fn(),
    })

    const { getByRole } = render(<AIChatPanel />)

    await user.click(getByRole('button', { name: '开始语音输入' }))
    expect(startRecording).toHaveBeenCalled()

    act(() => {
      latestSpeechOptions?.onResult?.('帮我分析今天的学习数据')
    })
    expect(sendMessage).toHaveBeenCalledWith('帮我分析今天的学习数据')
  })

  it('shows speech errors inline', () => {
    const { getByText } = render(<AIChatPanel />)

    act(() => {
      latestSpeechOptions?.onError?.('麦克风权限被拒绝')
    })
    expect(getByText('语音输入不可用：麦克风权限被拒绝')).toBeInTheDocument()
  })
})
