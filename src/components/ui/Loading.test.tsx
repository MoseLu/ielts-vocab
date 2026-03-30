import React from 'react'
import { render, screen } from '@testing-library/react'
import { Loading } from './Loading'

describe('Loading', () => {
  it('uses the shared centered loading container by default', () => {
    const { container } = render(<Loading text="Loading data" />)

    expect(screen.getByText('Loading data')).toBeInTheDocument()
    expect(container.querySelector('.loading-state')).not.toBeNull()
    expect(container.querySelector('.loading-spinner-shell')).not.toBeNull()
  })

  it('uses fullscreen loading centering when requested', () => {
    const { container } = render(<Loading text="Full screen" fullScreen />)

    expect(screen.getByText('Full screen')).toBeInTheDocument()
    expect(container.querySelector('.loading-state--global')).not.toBeNull()
  })

  it('uses page-height centering when requested', () => {
    const { container } = render(<Loading text="Page load" page />)

    expect(screen.getByText('Page load')).toBeInTheDocument()
    expect(container.querySelector('.loading-state--page')).not.toBeNull()
  })
})
