import React from 'react'
import { render, screen } from '@testing-library/react'
import { Button } from './Button'

describe('Button', () => {
  it('renders the primary variant by default', () => {
    render(<Button>Continue</Button>)

    const button = screen.getByRole('button', { name: 'Continue' })
    expect(button.className).toContain('bg-accent')
    expect(button.className).toContain('rounded-2xl')
  })

  it('renders loading state and disables interaction', () => {
    const { container } = render(<Button isLoading>Saving</Button>)

    const button = screen.getByRole('button', { name: 'Saving' })
    expect(button).toBeDisabled()
    expect(container.querySelector('svg.animate-spin')).not.toBeNull()
  })
})
