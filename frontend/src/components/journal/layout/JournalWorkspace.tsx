import type { ReactNode } from 'react'
import { Page, PageContent, PageHeader } from '../../layout'
import { UnderlineTabs } from '../../ui'

type JournalTab = 'today' | 'history'

interface JournalWorkspaceProps {
  activeTab: JournalTab
  onTabChange: (tab: JournalTab) => void
  actions?: ReactNode
  children: ReactNode
}

export default function JournalWorkspace({
  activeTab,
  onTabChange,
  actions,
  children,
}: JournalWorkspaceProps) {
  return (
    <Page className="journal-page">
      <PageHeader className="journal-topbar">
        <UnderlineTabs
          className="journal-tabs"
          ariaLabel="日记导航"
          value={activeTab}
          onChange={onTabChange}
          options={[
            { value: 'today', label: '今日复盘' },
            { value: 'history', label: '历史笔记' },
          ]}
        />

        {actions}
      </PageHeader>

      <PageContent className="journal-workspace-content">{children}</PageContent>
    </Page>
  )
}
