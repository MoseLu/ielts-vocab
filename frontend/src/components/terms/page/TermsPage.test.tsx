import React from 'react'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import TermsPage from './TermsPage'

describe('TermsPage', () => {
  it('renders agreement content and document navigation', () => {
    render(
      <MemoryRouter>
        <TermsPage />
      </MemoryRouter>,
    )

    expect(screen.getByRole('heading', { name: '用户服务协议' })).toBeInTheDocument()
    expect(screen.getByRole('complementary', { name: '文档列表' })).toBeInTheDocument()
    expect(screen.getByRole('navigation', { name: '本页目录' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: '用户服务协议' })).toHaveAttribute('href', '/terms')
  })
})
