import React from 'react'
import { render, screen } from '@testing-library/react'
import { EmptyState } from './EmptyState'

describe('EmptyState', () => {
  it('applies page-level class and renders content', () => {
    render(
      <EmptyState
        page
        title="No data"
        description="Nothing to show"
        action={<button>Retry</button>}
      />,
    )

    expect(screen.getByText('No data').closest('.empty-state--page')).not.toBeNull()
    expect(screen.getByText('Nothing to show')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Retry' })).toBeInTheDocument()
  })
})
