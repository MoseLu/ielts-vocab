import { render, screen } from '@testing-library/react'
import { vi } from 'vitest'

import { AdminDashboardView } from './AdminDashboardView'


describe('AdminDashboardView', () => {
  it('does not show the exams import tab', () => {
    render(
      <AdminDashboardView
        tab="overview"
        overview={null}
        overviewLoading={false}
        users={[]}
        feedbackItems={[]}
        feedbackTotal={0}
        total={0}
        page={1}
        pages={1}
        search=""
        sort="created_at"
        order="desc"
        loading={false}
        feedbackLoading={false}
        error=""
        onDismissError={vi.fn()}
        onTabChange={vi.fn()}
        onSearchSubmit={vi.fn()}
        onSearchClear={vi.fn()}
        onSearchChange={vi.fn()}
        onSort={vi.fn()}
        onPageChange={vi.fn()}
        onSelectUser={vi.fn()}
      />,
    )

    expect(screen.queryByText('真题导入')).not.toBeInTheDocument()
    expect(screen.getByText('平台概览')).toBeInTheDocument()
    expect(screen.getByText('用户管理')).toBeInTheDocument()
    expect(screen.getByText('问题反馈')).toBeInTheDocument()
  })
})
