import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { SegmentedControl, UnderlineTabs } from './NavigationControls'

describe('NavigationControls', () => {
  it('renders segmented control and updates active option', async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()

    render(
      <SegmentedControl
        value="overview"
        onChange={onChange}
        ariaLabel="admin tabs"
        options={[
          { value: 'overview', label: '平台概览' },
          { value: 'users', label: '用户管理', badge: 12 },
        ]}
      />,
    )

    expect(screen.getByRole('tab', { name: /平台概览/i })).toHaveAttribute('aria-selected', 'true')
    expect(screen.getByText('12')).toBeInTheDocument()

    await user.click(screen.getByRole('tab', { name: /用户管理/i }))
    expect(onChange).toHaveBeenCalledWith('users')
  })

  it('renders underline tabs and supports stretch mode', async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()

    render(
      <UnderlineTabs
        value="login"
        onChange={onChange}
        stretch
        ariaLabel="auth tabs"
        options={[
          { value: 'login', label: '登录' },
          { value: 'register', label: '注册' },
        ]}
      />,
    )

    expect(screen.getByRole('tab', { name: '登录' })).toHaveAttribute('aria-selected', 'true')

    await user.click(screen.getByRole('tab', { name: '注册' }))
    expect(onChange).toHaveBeenCalledWith('register')
  })

  it('uses middle as the default underline tab size', () => {
    render(
      <UnderlineTabs
        value="login"
        onChange={() => {}}
        ariaLabel="default sized tabs"
        options={[
          { value: 'login', label: '登录' },
          { value: 'register', label: '注册' },
        ]}
      />,
    )

    expect(screen.getByRole('tablist', { name: 'default sized tabs' })).toHaveClass('underline-tabs--middle')
    expect(screen.getByRole('tab', { name: '登录' })).toHaveClass('underline-tabs__item--middle')
  })
})
