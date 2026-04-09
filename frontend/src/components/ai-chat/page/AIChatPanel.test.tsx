import React from 'react'
import { act, render } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import AIChatPanel from './AIChatPanel'

const useAIChatMock = vi.fn()
const useSpeechRecognitionMock = vi.fn()
let latestSpeechOptions:
  | {
    enabled?: boolean
    language?: string
    enableVad?: boolean
    autoStop?: boolean
    autoStopDelay?: number
    enableBrowserRecognition?: boolean
    enableRealtimeRecognition?: boolean
    onResult?: (text: string) => void
    onPartial?: (text: string) => void
    onError?: (error: string) => void
    onLevel?: (level: number) => void
  }
  | null = null

vi.mock('../../../hooks/useAIChat', () => ({
  useAIChat: () => useAIChatMock(),
}))

vi.mock('../../../hooks/useSpeechRecognition', () => ({
  useSpeechRecognition: (options: {
    onResult?: (text: string) => void
    onPartial?: (text: string) => void
    onError?: (error: string) => void
    onLevel?: (level: number) => void
  }) => {
    latestSpeechOptions = options
    return useSpeechRecognitionMock(options)
  },
}))

vi.mock('../../ui/Scrollbar', () => ({
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
      isProcessing: false,
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

  afterEach(() => {
    vi.useRealTimers()
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
    expect(container.querySelector('.ai-panel.ai-panel--fullscreen')).not.toBeNull()

    await user.click(toggleButton)
    expect(container.querySelector('.ai-panel.ai-panel--fullscreen')).toBeNull()

    await user.click(toggleButton)
    expect(container.querySelector('.ai-panel.ai-panel--fullscreen')).not.toBeNull()
  })

  it('removes the idle speech hint from the input footer', () => {
    const { getByPlaceholderText, queryByText } = render(<AIChatPanel />)

    expect(getByPlaceholderText('输入问题，或发送学习指令')).toBeInTheDocument()
    expect(queryByText('点击麦克风即可语音提问')).toBeNull()
  })

  it('reveals starter actions only after the user expands the launcher', async () => {
    const user = userEvent.setup()
    useAIChatMock.mockReturnValue({
      messages: [
        {
          id: 'greet',
          role: 'assistant',
          content: '你好，我可以帮你安排今天的学习。',
          options: ['帮我安排今天复习'],
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

    const { getByRole, queryByRole, getByText } = render(<AIChatPanel />)

    expect(queryByRole('button', { name: '帮我安排今天复习' })).toBeNull()
    expect(queryByRole('button', { name: '发音训练' })).toBeNull()
    expect(getByText('你好，我可以帮你安排今天的学习。')).toBeInTheDocument()

    await user.click(getByRole('button', { name: '看看常见任务' }))

    expect(getByRole('button', { name: '帮我安排今天复习' })).toBeInTheDocument()
    expect(getByRole('button', { name: '发音训练' })).toBeInTheDocument()
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
    await user.click(getByRole('button', { name: '看看常见任务' }))
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

  it('keeps the final transcript in the composer instead of auto-sending it', async () => {
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
      isProcessing: false,
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

    expect(getByRole('textbox')).toHaveValue('帮我分析今天的学习数据')
    expect(sendMessage).not.toHaveBeenCalled()
  })

  it('accumulates multiple finalized speech segments in the composer', async () => {
    const user = userEvent.setup()
    const startRecording = vi.fn().mockResolvedValue(undefined)

    useAIChatMock.mockReturnValue({
      messages: [],
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
      isProcessing: false,
      isReady: false,
      startRecording,
      stopRecording: vi.fn(),
    })

    const { getByRole } = render(<AIChatPanel />)

    await user.click(getByRole('button', { name: '开始语音输入' }))

    act(() => {
      latestSpeechOptions?.onResult?.('第一段')
      latestSpeechOptions?.onPartial?.('第二段草稿')
    })
    expect(getByRole('textbox')).toHaveValue('第一段 第二段草稿')

    act(() => {
      latestSpeechOptions?.onResult?.('第二段')
    })
    expect(getByRole('textbox')).toHaveValue('第一段 第二段')
  })

  it('replaces the previous speech-only transcript when starting a fresh recording', async () => {
    const user = userEvent.setup()
    const startRecording = vi.fn().mockResolvedValue(undefined)

    useAIChatMock.mockReturnValue({
      messages: [],
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
      isProcessing: false,
      isReady: false,
      startRecording,
      stopRecording: vi.fn(),
    })

    const { getByRole } = render(<AIChatPanel />)

    await user.click(getByRole('button', { name: '开始语音输入' }))
    act(() => {
      latestSpeechOptions?.onResult?.('The widespread adoption of renewable energy sources')
    })
    expect(getByRole('textbox')).toHaveValue('The widespread adoption of renewable energy sources')

    await user.click(getByRole('button', { name: '开始语音输入' }))
    act(() => {
      latestSpeechOptions?.onResult?.('嗯嗯')
    })

    expect(getByRole('textbox')).toHaveValue('嗯嗯')
  })

  it('uses manual stop speech settings for the ai assistant', () => {
    render(<AIChatPanel />)

    expect(latestSpeechOptions).toMatchObject({
      enabled: true,
      language: 'zh',
      enableVad: false,
      autoStop: false,
      enableBrowserRecognition: false,
      enableRealtimeRecognition: true,
    })
  })

  it('shows a loading mic state while speech is being finalized', () => {
    useAIChatMock.mockReturnValue({
      messages: [],
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
      isProcessing: true,
      isReady: false,
      startRecording: vi.fn().mockResolvedValue(undefined),
      stopRecording: vi.fn(),
    })

    const { container, getByRole, queryByText } = render(<AIChatPanel />)

    expect(getByRole('button', { name: '语音转写中' })).toBeDisabled()
    expect(container.querySelector('.ai-voice-btn-spinner')).not.toBeNull()
    expect(container.querySelector('.ai-voice-visualizer--processing')).not.toBeNull()
    expect(queryByText('正在转写，请稍候...')).toBeNull()
  })

  it('raises waveform peaks as speech levels increase', () => {
    vi.useFakeTimers()
    useAIChatMock.mockReturnValue({
      messages: [],
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
      isRecording: true,
      isProcessing: false,
      isReady: true,
      startRecording: vi.fn().mockResolvedValue(undefined),
      stopRecording: vi.fn(),
    })

    const { container, getByText } = render(<AIChatPanel />)

    act(() => {
      latestSpeechOptions?.onLevel?.(0.95)
      vi.advanceTimersByTime(160)
    })

    expect(getByText('0:00')).toBeInTheDocument()
    expect(container.querySelector('.ai-voice-bar--wave')).not.toBeNull()
  })

  it('streams partial speech results into the composer', async () => {
    const user = userEvent.setup()
    const startRecording = vi.fn().mockResolvedValue(undefined)

    useAIChatMock.mockReturnValue({
      messages: [],
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
      isProcessing: false,
      isReady: false,
      startRecording,
      stopRecording: vi.fn(),
    })

    const { container, getByRole, queryByText } = render(<AIChatPanel />)

    await user.click(getByRole('button', { name: '开始语音输入' }))
    expect(startRecording).toHaveBeenCalled()

    act(() => {
      latestSpeechOptions?.onPartial?.('帮我分析今天的学习数据')
    })

    expect(getByRole('textbox')).toHaveValue('帮我分析今天的学习数据')
    expect(container.querySelector('.ai-voice-visualizer')).toBeNull()
    expect(queryByText('正在听写，内容会实时进入输入框')).toBeNull()
  })

  it('shows speech errors inline', () => {
    const { getByText } = render(<AIChatPanel />)

    act(() => {
      latestSpeechOptions?.onError?.('麦克风权限被拒绝')
    })
    expect(getByText('语音输入不可用：麦克风权限被拒绝')).toBeInTheDocument()
  })
})
