import React from 'react'
import { render, screen } from '@testing-library/react'
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

  it('renders assistant messages as markdown and supports fullscreen toggle', async () => {
    const user = userEvent.setup()
    const { container } = render(<AIChatPanel />)

    expect(container.querySelector('.ai-markdown-content h1')?.textContent).toBe('Study Plan')
    expect(container.querySelectorAll('.ai-markdown-content li')).toHaveLength(2)

    await user.click(screen.getByRole('button', { name: '全屏显示' }))
    expect(container.querySelector('.ai-panel.ai-panel--fullscreen')).not.toBeNull()

    await user.click(screen.getByRole('button', { name: '还原窗口' }))
    expect(container.querySelector('.ai-panel.ai-panel--fullscreen')).toBeNull()
  })
})
