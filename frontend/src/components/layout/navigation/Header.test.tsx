import React from 'react'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'
import Header from './Header'
import { GLOBAL_WORD_SEARCH_OPEN_EVENT } from './globalWordSearchEvents'
import { clearPlanHelpFaqItems, setPlanHelpFaqItems } from './helpContentRegistry'

const updateUserMock = vi.fn()

vi.mock('../../../contexts', () => ({
  useAuth: () => ({ updateUser: updateUserMock, isAdmin: false }),
}))

vi.mock('../../profile/avatar/AvatarUpload', () => ({
  default: () => null,
}))

vi.mock('../../settings/SettingsPanel', () => ({
  default: () => null,
}))

vi.mock('../../ui/Popover', () => ({
  default: ({ trigger, children }: { trigger: React.ReactNode; children: React.ReactNode }) => <>{trigger}{children}</>,
}))

vi.mock('../../ui/Scrollbar', () => ({
  Scrollbar: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}))

describe('Header', () => {
  beforeEach(() => {
    updateUserMock.mockReset()
    clearPlanHelpFaqItems()
  })

  it('keeps speaking navigation out of the desktop header to avoid duplicating the sidebar entry', () => {
    render(
      <MemoryRouter>
        <Header
          user={{ username: 'luo', email: 'luo@example.com', avatar_url: null }}
          currentDay={1}
          onLogout={vi.fn()}
        />
      </MemoryRouter>,
    )

    expect(screen.queryByRole('button', { name: '口语' })).not.toBeInTheDocument()
  })

  it('renders 真题 in the top navigation immediately after 词书', () => {
    render(
      <MemoryRouter>
        <Header
          user={{ username: 'luo', email: 'luo@example.com', avatar_url: null }}
          currentDay={1}
          onLogout={vi.fn()}
        />
      </MemoryRouter>,
    )

    const navButtons = screen.getAllByRole('button').filter(button => (
      ['学习中心', '词书', '真题'].includes(button.textContent || '')
    ))

    expect(navButtons.map(button => button.textContent)).toEqual(['学习中心', '词书', '真题'])
  })

  it('keeps 真题 active on nested exam routes', () => {
    render(
      <MemoryRouter initialEntries={['/exams/12']}>
        <Header
          user={{ username: 'luo', email: 'luo@example.com', avatar_url: null }}
          currentDay={1}
          onLogout={vi.fn()}
        />
      </MemoryRouter>,
    )

    expect(screen.getByRole('button', { name: '真题' })).toHaveClass('active')
  })

  it('dispatches the global word search event when the search icon is clicked', async () => {
    const user = userEvent.setup()
    const listener = vi.fn()
    window.addEventListener(GLOBAL_WORD_SEARCH_OPEN_EVENT, listener as EventListener)

    render(
      <MemoryRouter>
        <Header
          user={{ username: 'luo', email: 'luo@example.com', avatar_url: null }}
          currentDay={1}
          onLogout={vi.fn()}
        />
      </MemoryRouter>,
    )

    await user.click(screen.getByRole('button', { name: '打开全局单词搜索' }))

    expect(listener).toHaveBeenCalledTimes(1)

    window.removeEventListener(GLOBAL_WORD_SEARCH_OPEN_EVENT, listener as EventListener)
  })

  it('renders the help modal in a portal and restores scroll lock when closed', async () => {
    const user = userEvent.setup()

    render(
      <MemoryRouter>
        <Header
          user={{ username: 'luo', email: 'luo@example.com', avatar_url: null }}
          currentDay={1}
          onLogout={vi.fn()}
        />
      </MemoryRouter>,
    )

    await user.click(screen.getByRole('button', { name: '帮助' }))

    const helpTitle = screen.getByRole('heading', { name: '帮助' })
    expect(document.body).toContainElement(helpTitle)
    expect(document.body.style.overflow).toBe('hidden')

    await user.keyboard('{Escape}')

    expect(screen.queryByRole('heading', { name: '帮助' })).not.toBeInTheDocument()
    expect(document.body.style.overflow).toBe('')
  })

  it('filters homepage faq items inside the help modal search', async () => {
    const user = userEvent.setup()

    setPlanHelpFaqItems([
      {
        id: 'wrong-words',
        eyebrow: '错词本',
        title: '错词怎么减少',
        badge: '连续答对 4 次',
        description: '错词要按能力项分别清理。',
        facts: ['当前：12 词待清'],
        sections: [
          {
            label: '怎么变少',
            items: ['同一项连续答对 4 次后才会从待清里消掉。'],
          },
        ],
        tone: 'error',
      },
      {
        id: 'ebbinghaus',
        eyebrow: '艾宾浩斯',
        title: '复习怎样算完成',
        badge: '6 词到期',
        description: '当天到期词清零才算今天完成。',
        facts: ['频次：1 天 / 4 天 / 7 天'],
        sections: [
          {
            label: '今天算完成',
            items: ['完成标准是到期待复习数量归零。'],
          },
        ],
        tone: 'accent',
      },
    ])

    render(
      <MemoryRouter initialEntries={['/plan']}>
        <Header
          user={{ username: 'luo', email: 'luo@example.com', avatar_url: null }}
          currentDay={1}
          onLogout={vi.fn()}
        />
      </MemoryRouter>,
    )

    await user.click(screen.getByRole('button', { name: '帮助' }))

    expect(screen.getByText('错词怎么减少')).toBeInTheDocument()
    expect(screen.getByText('复习怎样算完成')).toBeInTheDocument()

    await user.type(screen.getByRole('searchbox', { name: '搜索帮助内容' }), '艾宾浩斯')

    expect(screen.getByText('复习怎样算完成')).toBeInTheDocument()
    expect(screen.queryByText('错词怎么减少')).not.toBeInTheDocument()
    expect(screen.getByText('当前匹配 1 项帮助内容')).toBeInTheDocument()
  })
})
