import React from 'react'
import { render, screen, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import QaHistoryDocument from './QaHistoryDocument'

vi.mock('../../../lib/journalMarkdown', () => ({
  renderJournalMarkdown: vi.fn(() => '<p>mock html</p>'),
}))

describe('QaHistoryDocument', () => {
  it('shows sidebar and document skeletons while notes are loading', () => {
    const { container } = render(
      <QaHistoryDocument
        notes={[]}
        notesLoading
        notesError=""
        notesTotal={0}
        selectedNote={null}
        cursorStack={[null]}
        hasMore={false}
        onSelectNote={() => {}}
        onPreviousPage={() => {}}
        onNextPage={() => {}}
        formatDateTime={() => '2026-03-30 12:00'}
        toPlainTextSnippet={(text: string) => text}
      />,
    )

    expect(container.querySelector('.journal-doc-skeleton')).not.toBeNull()
    expect(container.querySelector('.journal-loading')).toBeNull()
  })

  it('renders memory cues for repeated topics and related history around the selected note', () => {
    render(
      <QaHistoryDocument
        notes={[
          {
            id: 1,
            question: 'kind of 和 a kind of 有什么区别？',
            answer: '第一次解释',
            word_context: 'kind',
            created_at: '2026-03-30T09:00:00',
          },
          {
            id: 2,
            question: 'kind of 和 a kind of 还是分不清',
            answer: '第二次解释',
            word_context: 'kind',
            created_at: '2026-03-30T10:00:00',
          },
          {
            id: 3,
            question: 'evidence 和 proof 的区别？',
            answer: '另一个主题',
            word_context: 'evidence',
            created_at: '2026-03-30T11:00:00',
          },
        ]}
        notesLoading={false}
        notesError=""
        notesTotal={3}
        selectedNote={{
          id: 2,
          question: 'kind of 和 a kind of 还是分不清',
          answer: '第二次解释',
          word_context: 'kind',
          created_at: '2026-03-30T10:00:00',
        }}
        cursorStack={[null]}
        hasMore={false}
        onSelectNote={() => {}}
        onPreviousPage={() => {}}
        onNextPage={() => {}}
        formatDateTime={() => '2026-03-30 10:00'}
        toPlainTextSnippet={(text: string) => text}
      />,
    )

    expect(screen.getByText('重复追问主题')).toBeInTheDocument()
    expect(screen.getByText('相关历史问题')).toBeInTheDocument()
    const relatedHistory = screen.getByText('相关历史问题').closest('section')
    expect(relatedHistory).not.toBeNull()
    expect(within(relatedHistory!).getByText('kind of 和 a kind of 有什么区别？')).toBeInTheDocument()
    expect(screen.getByText('当前主题已追问 2 次')).toBeInTheDocument()
  })
})
