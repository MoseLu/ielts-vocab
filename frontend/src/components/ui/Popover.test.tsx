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
