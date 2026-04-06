import React from 'react'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'
import Header from './Header'
import { GLOBAL_WORD_SEARCH_OPEN_EVENT } from './globalWordSearchEvents'

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
})
