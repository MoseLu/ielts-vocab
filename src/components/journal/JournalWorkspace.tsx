import type { ReactNode } from 'react'
import { Page, PageContent, PageHeader } from '../layout'
import { UnderlineTabs } from '../ui'

type JournalTab = 'summaries' | 'notes'

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
          ariaLabel="学习日志导航"
          value={activeTab}
          onChange={onTabChange}
          options={[
            { value: 'summaries', label: '每日总结' },
            { value: 'notes', label: '问答历史' },
          ]}
        />

        {actions}
      </PageHeader>

      <PageContent className="journal-workspace-content">{children}</PageContent>
    </Page>
  )
}
