import React from 'react'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import Popover from './Popover'

const floatingState = vi.hoisted(() => ({
  x: undefined as number | undefined,
  y: undefined as number | undefined,
}))

vi.mock('@floating-ui/react', () => ({
  useFloating: () => ({
    refs: {
      setReference: vi.fn(),
      setFloating: vi.fn(),
      reference: { current: document.createElement('div') },
      floating: { current: document.createElement('div') },
    },
    x: floatingState.x,
    y: floatingState.y,
    strategy: 'fixed',
    placement: 'bottom',
    middlewareData: { arrow: {} },
  }),
  autoUpdate: vi.fn(),
  offset: vi.fn(() => ({})),
  flip: vi.fn(() => ({})),
  shift: vi.fn(() => ({})),
  arrow: vi.fn(() => ({})),
  size: vi.fn(() => ({})),
}))

describe('Popover', () => {
  beforeEach(() => {
    floatingState.x = undefined
    floatingState.y = undefined
  })

  it('keeps the panel hidden until Floating UI resolves coordinates', async () => {
    const user = userEvent.setup()

    render(
      <Popover
        trigger={<button type="button">Open</button>}
      >
        <div>Panel content</div>
      </Popover>,
    )

    await user.click(screen.getByRole('button', { name: 'Open' }))

    const panel = screen.getByText('Panel content').closest('.popover-panel') as HTMLDivElement
    expect(panel.style.visibility).toBe('hidden')
  })

  it('merges trigger props onto the provided button instead of wrapping it in a div', async () => {
    const user = userEvent.setup()

    const { container } = render(
      <Popover
        trigger={<button type="button">Avatar</button>}
      >
        <div>Menu</div>
      </Popover>,
    )

    const trigger = screen.getByRole('button', { name: 'Avatar' })
    expect(trigger.tagName).toBe('BUTTON')
    expect(container.querySelector('.popover-trigger')).toBeNull()

    await user.click(trigger)
    expect(trigger).toHaveAttribute('aria-expanded', 'true')
    expect(trigger).toHaveAttribute('aria-controls')
    expect(trigger).not.toHaveAttribute('aria-haspopup')
  })

  it('preserves a forwarded trigger ref while registering the floating reference', () => {
    const triggerRef = React.createRef<HTMLButtonElement>()
    const Trigger = React.forwardRef<HTMLButtonElement>((_, ref) => (
      <button ref={ref} type="button">Forwarded trigger</button>
    ))

    render(
      <Popover trigger={<Trigger ref={triggerRef} />}>
        <div>Menu</div>
      </Popover>,
    )

    expect(triggerRef.current).toBe(screen.getByRole('button', { name: 'Forwarded trigger' }))
    expect(screen.getByRole('button', { name: 'Forwarded trigger' })).toBeInTheDocument()
  })

  it('positions the panel with resolved coordinates', async () => {
    const user = userEvent.setup()
    floatingState.x = 160
    floatingState.y = 48

    render(
      <Popover
        trigger={<button type="button">Open</button>}
      >
        <div>Anchored content</div>
      </Popover>,
    )

    await user.click(screen.getByRole('button', { name: 'Open' }))

    const panel = screen.getByText('Anchored content').closest('.popover-panel') as HTMLDivElement
    expect(panel.style.left).toBe('160px')
    expect(panel.style.top).toBe('48px')
  })
})
