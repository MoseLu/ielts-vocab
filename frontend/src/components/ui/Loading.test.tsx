import React from 'react'
import { render, screen } from '@testing-library/react'
import { Loading, MicroLoading, PageReady, PageSkeleton } from './Loading'

describe('Loading', () => {
  it('uses the shared centered loading container by default', () => {
    const { container } = render(<Loading />)

    expect(screen.getByText('加载中...')).toBeInTheDocument()
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

  it('renders a shared page skeleton variant', () => {
    const { container } = render(<PageSkeleton variant="stats" />)

    expect(container.querySelector('.page-skeleton')).not.toBeNull()
    expect(container.querySelector('.page-skeleton--stats')).not.toBeNull()
    expect(container.querySelectorAll('.ui-skeleton').length).toBeGreaterThan(0)
  })

  it('supports configurable skeleton counts per page', () => {
    const { container } = render(
      <>
        <PageSkeleton variant="books" itemCount={4} />
        <PageSkeleton variant="stats" metricCount={9} />
      </>,
    )

    expect(container.querySelectorAll('.page-skeleton--books .page-skeleton-card--book')).toHaveLength(4)
    expect(container.querySelectorAll('.page-skeleton--stats .page-skeleton-card--metric')).toHaveLength(9)
  })

  it('renders a shared micro-loading treatment for inline async states', () => {
    const { container } = render(<MicroLoading text="保存中..." />)

    expect(screen.getByText('保存中...')).toBeInTheDocument()
    expect(container.querySelector('.micro-loading')).not.toBeNull()
    expect(container.querySelector('.micro-loading__spinner')).not.toBeNull()
  })

  it('renders the skeleton until page content is ready', () => {
    const { container, rerender } = render(
      <PageReady ready={false} fallback={<PageSkeleton variant="journal" />}>
        <div>Ready content</div>
      </PageReady>,
    )

    expect(container.querySelector('.page-skeleton--journal')).not.toBeNull()
    expect(screen.queryByText('Ready content')).not.toBeInTheDocument()

    rerender(
      <PageReady ready>
        <div>Ready content</div>
      </PageReady>,
    )

    expect(screen.getByText('Ready content')).toBeInTheDocument()
    expect(container.querySelector('.page-skeleton')).toBeNull()
  })
})
