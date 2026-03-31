import React from 'react'
import { render } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import AIChatPanel from './AIChatPanel'

const useAIChatMock = vi.fn()

vi.mock('../hooks/useAIChat', () => ({
  useAIChat: () => useAIChatMock(),
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

    Object.defineProperty(window.HTMLElement.prototype, 'scrollIntoView', {
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
})
