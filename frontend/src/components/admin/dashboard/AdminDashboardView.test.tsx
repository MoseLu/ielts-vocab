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
        assetItems={[]}
        feedbackTotal={0}
        assetTotal={0}
        assetSummary={null}
        total={0}
        page={1}
        pages={1}
        assetPage={1}
        assetPages={1}
        search=""
        assetSearch=""
        assetBookId=""
        assetMnemonicStatus="all"
        sort="created_at"
        order="desc"
        loading={false}
        feedbackLoading={false}
        assetLoading={false}
        error=""
        onDismissError={vi.fn()}
        onTabChange={vi.fn()}
        onSearchSubmit={vi.fn()}
        onSearchClear={vi.fn()}
        onSearchChange={vi.fn()}
        onAssetSearchSubmit={vi.fn()}
        onAssetSearchClear={vi.fn()}
        onAssetSearchChange={vi.fn()}
        onAssetBookChange={vi.fn()}
        onAssetMnemonicStatusChange={vi.fn()}
        onAssetPageChange={vi.fn()}
        onSort={vi.fn()}
        onPageChange={vi.fn()}
        onSelectUser={vi.fn()}
      />,
    )

    expect(screen.queryByText('真题导入')).not.toBeInTheDocument()
    expect(screen.getByText('平台概览')).toBeInTheDocument()
    expect(screen.getByText('用户管理')).toBeInTheDocument()
    expect(screen.getByText('问题反馈')).toBeInTheDocument()
    expect(screen.getByText('资产管理')).toBeInTheDocument()
  })
})
