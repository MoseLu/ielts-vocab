import React from 'react'
import { render, screen } from '@testing-library/react'
import { Button } from './Button'

describe('Button', () => {
  it('renders the primary variant by default', () => {
    render(<Button>Continue</Button>)

    const button = screen.getByRole('button', { name: 'Continue' })
    expect(button.className).toContain('ui-button')
    expect(button.className).toContain('ui-button--primary')
  })

  it('renders loading state and disables interaction', () => {
    const { container } = render(<Button isLoading>Saving</Button>)

    const button = screen.getByRole('button', { name: 'Saving' })
    expect(button).toBeDisabled()
    expect(container.querySelector('svg.ui-button__spinner.loading-spin')).not.toBeNull()
  })
})
