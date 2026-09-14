import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import LearningJournalPage from './LearningJournalPage'

const apiFetchMock = vi.fn()
const tiptapMockState = vi.hoisted(() => ({
  config: null as { onUpdate?: (value: { editor: { getHTML: () => string } }) => void } | null,
  listeners: new Map<string, EventListener>(),
}))

vi.mock('../../../lib', async () => {
  const actual = await vi.importActual<typeof import('../../../lib')>('../../../lib')
  return {
    ...actual,
    apiFetch: (...args: unknown[]) => apiFetchMock(...args),
  }
})

vi.mock('@tiptap/react', () => ({
  EditorContent: ({ className }: { className?: string }) => (
    <div className={className}>
      <div className="journal-editor-content" />
    </div>
  ),
  useEditor: (config: { content?: string; onUpdate?: (value: { editor: { getHTML: () => string } }) => void }) => {
    tiptapMockState.config = config
    return ({
      commands: { setContent: vi.fn() },
      getHTML: () => config.content || '<p></p>',
      view: {
        dom: {
          addEventListener: vi.fn((type: string, handler: EventListener) => {
            tiptapMockState.listeners.set(type, handler)
          }),
          removeEventListener: vi.fn((type: string) => {
            tiptapMockState.listeners.delete(type)
          }),
        },
      },
    })
  },
}))

const todayEntry = {
  id: 1,
  date: '2026-06-03',
  content: '# 你好\n\n今天复习了 attention。',
  polished_content: null,
  created_at: '2026-06-03T04:00:00',
  updated_at: '2026-06-03T04:31:00',
}

const journalHistoryStyles = readFileSync(
  resolve(process.cwd(), 'src/styles/pages/journal/_journal-history.scss'),
  'utf-8',
)

describe('LearningJournalPage diary view', () => {
  beforeEach(() => {
    apiFetchMock.mockReset()
    tiptapMockState.config = null
    tiptapMockState.listeners.clear()
    vi.spyOn(window, 'alert').mockImplementation(() => {})
  })

  it('shows a page loading gate before the today entry resolves', async () => {
    let resolveToday: ((value: { entry: null }) => void) | null = null
    apiFetchMock.mockImplementation((url: string) => {
      if (url === '/api/notes/journal/today') {
        return new Promise(resolve => {
          resolveToday = resolve
        })
      }
      return Promise.reject(new Error(`Unexpected url: ${url}`))
    })

    const { container } = render(<LearningJournalPage />)

    expect(container.querySelector('.page-skeleton--journal')).not.toBeNull()
    resolveToday?.({ entry: null })

    await screen.findByRole('tab', { name: '今日复盘' })
  })

  it('renders the today diary entry and keeps the old summary tabs out', async () => {
    apiFetchMock.mockImplementation((url: string) => {
      if (url === '/api/notes/journal/today') {
        return Promise.resolve({ entry: todayEntry })
      }
      return Promise.reject(new Error(`Unexpected url: ${url}`))
    })

    const { container } = render(<LearningJournalPage />)

    expect(await screen.findByRole('tab', { name: '今日复盘' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: '历史笔记' })).toBeInTheDocument()
    expect(screen.queryByRole('tab', { name: '每日总结' })).not.toBeInTheDocument()
    expect(screen.queryByRole('tab', { name: '问答历史' })).not.toBeInTheDocument()
    expect(container.querySelector('.journal-doc-shell--today')).not.toBeNull()
    expect(container.querySelector('.journal-doc-body h1')?.textContent).toContain('你好')
    expect(screen.getByRole('button', { name: '编辑今日复盘' })).toBeInTheDocument()
  })

  it('renders diary images as capped top attachments', async () => {
    const user = userEvent.setup()
    const imageMarkdown = Array.from({ length: 4 }, (_, index) => (
      `![image-${index + 1}](data:image/png;base64,card${index + 1})`
    )).join('\n')
    apiFetchMock.mockImplementation((url: string) => {
      if (url === '/api/notes/journal/today') {
        return Promise.resolve({
          entry: {
            ...todayEntry,
            content: `# 你好\n\n${imageMarkdown}`,
          },
        })
      }
      return Promise.reject(new Error(`Unexpected url: ${url}`))
    })

    const { container } = render(<LearningJournalPage />)

    expect(await screen.findByText('图片附件')).toBeInTheDocument()
    expect(container.querySelector('.journal-today-stack')).not.toBeNull()
    const imagePanel = container.querySelector('.journal-image-panel')
    const body = container.querySelector('.journal-doc-body')
    expect(imagePanel).not.toBeNull()
    expect(body).not.toBeNull()
    expect(imagePanel!.compareDocumentPosition(body!) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(container.querySelectorAll('.journal-image-card:not(.journal-image-card--add)')).toHaveLength(3)
    expect(screen.getByText('3/3')).toBeInTheDocument()
    expect(body?.textContent).not.toContain('image-1')

    await user.click(screen.getByRole('button', { name: '预览图片 1' }))

    expect(await screen.findByRole('dialog', { name: '日记图片预览' })).toBeInTheDocument()
    expect(screen.getByAltText('日记图片预览 1')).toHaveAttribute('src', 'data:image/png;base64,card1')

    await user.click(screen.getByRole('button', { name: '关闭日记图片预览' }))

    expect(screen.queryByRole('dialog', { name: '日记图片预览' })).not.toBeInTheDocument()
  })

  it('does not render the insert-image context menu after reaching the image limit', async () => {
    const imageMarkdown = Array.from({ length: 3 }, (_, index) => (
      `![image-${index + 1}](data:image/png;base64,card${index + 1})`
    )).join('\n')
    apiFetchMock.mockImplementation((url: string) => {
      if (url === '/api/notes/journal/today') {
        return Promise.resolve({
          entry: {
            ...todayEntry,
            content: `# 你好\n\n${imageMarkdown}`,
          },
        })
      }
      return Promise.reject(new Error(`Unexpected url: ${url}`))
    })

    const user = userEvent.setup()
    render(<LearningJournalPage />)
    await user.click(await screen.findByRole('button', { name: '编辑今日复盘' }))

    await waitFor(() => expect(tiptapMockState.listeners.has('contextmenu')).toBe(true))
    tiptapMockState.listeners.get('contextmenu')?.(new MouseEvent('contextmenu', { clientX: 10, clientY: 20, cancelable: true }))

    expect(screen.queryByRole('menu')).not.toBeInTheDocument()
    expect(screen.queryByText('插入图片')).not.toBeInTheDocument()
  })

  it('loads history entries after switching to the history tab', async () => {
    const user = userEvent.setup()
    apiFetchMock.mockImplementation((url: string) => {
      if (url === '/api/notes/journal/today') {
        return Promise.resolve({ entry: todayEntry })
      }
      if (url.startsWith('/api/notes/journal?')) {
        return Promise.resolve({
          entries: [
            {
              ...todayEntry,
              id: 2,
              date: '2026-06-02',
              content: [
                '昨天记录了 listening practice。',
                '![image-1](data:image/png;base64,history1)',
                '![image-2](data:image/png;base64,history2)',
              ].join('\n\n'),
            },
          ],
          has_more: false,
        })
      }
      return Promise.reject(new Error(`Unexpected url: ${url}`))
    })

    const { container } = render(<LearningJournalPage />)
    await user.click(await screen.findByRole('tab', { name: '历史笔记' }))

    await screen.findByText('2026-06-02')
    expect(screen.getByText('更新 04:31')).toBeInTheDocument()
    expect(screen.queryByText('2026-06-03 04:31')).not.toBeInTheDocument()
    expect(container.querySelector('.journal-date-range-field')).not.toBeNull()
    expect(container.querySelector('#journal-start-date')).toHaveAttribute('type', 'text')
    expect(container.querySelector('#journal-start-date')).toHaveAttribute('placeholder', '开始日期')
    expect(container.querySelector('#journal-start-date')).toHaveAttribute('readonly')
    expect(container.querySelector('#journal-end-date')).toHaveAttribute('type', 'text')
    expect(container.querySelector('#journal-end-date')).toHaveAttribute('placeholder', '结束日期')
    expect(container.querySelector('#journal-end-date')).toHaveAttribute('readonly')
    expect(container.querySelector('.journal-date-range-field')?.textContent).not.toContain('开始日期')
    expect(container.querySelector('.journal-date-range-field')?.textContent).not.toContain('结束日期')
    await user.click(screen.getByLabelText('开始日期'))
    const pickerDialog = screen.getByRole('dialog', { name: '选择日记日期范围' })
    expect(pickerDialog).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '上星期' })).toBeInTheDocument()
    expect(screen.getAllByText(/2026年/)).not.toHaveLength(0)
    const historyRequestsBeforeDraftEdit = apiFetchMock.mock.calls.filter(([url]) => (
      typeof url === 'string' && url.startsWith('/api/notes/journal?')
    )).length
    await user.type(within(pickerDialog).getByPlaceholderText('开始日期'), '2026/06/01')
    expect(apiFetchMock.mock.calls.filter(([url]) => (
      typeof url === 'string' && url.startsWith('/api/notes/journal?')
    ))).toHaveLength(historyRequestsBeforeDraftEdit)
    await user.click(screen.getByRole('button', { name: '好的' }))
    await waitFor(() => expect(apiFetchMock.mock.calls.filter(([url]) => (
      typeof url === 'string' && url.startsWith('/api/notes/journal?')
    )).length).toBeGreaterThan(historyRequestsBeforeDraftEdit))
    const preview = container.querySelector('.journal-history-card__preview')
    expect(preview?.textContent).toContain('listening practice')
    expect(preview?.textContent).not.toContain('[图片]')
    const cardImages = container.querySelectorAll('.journal-history-card__image img')
    expect(cardImages).toHaveLength(2)
    expect(cardImages[0]).toHaveAttribute('src', 'data:image/png;base64,history1')

    await user.click(container.querySelector('.journal-history-card')!)
    await screen.findByText('2026-06-02 笔记')
    const detailImages = container.querySelectorAll('.journal-history-detail-images img')
    expect(detailImages).toHaveLength(2)
    expect(detailImages[1]).toHaveAttribute('src', 'data:image/png;base64,history2')
  })

  it('keeps history cards compact instead of stretching a single row', () => {
    expect(journalHistoryStyles).toMatch(/\.journal-doc-shell--history\s*\{[^}]*align-content:\s*start;/s)
    expect(journalHistoryStyles).toMatch(/\.journal-history-grid\s*\{[^}]*align-items:\s*start;/s)
    expect(journalHistoryStyles).toMatch(/\.journal-history-card\s*\{[^}]*align-self:\s*start;/s)
  })

  it('saves edited recap content and can request polish', async () => {
    const user = userEvent.setup()
    apiFetchMock.mockImplementation((url: string) => {
      if (url === '/api/notes/journal/today') {
        return Promise.resolve({ entry: todayEntry })
      }
      if (url === '/api/notes/journal') {
        return Promise.resolve({
          entry: { ...todayEntry, content: '更新后的内容' },
        })
      }
      if (url === '/api/notes/journal/polish') {
        return Promise.resolve({ polished: '润色后的内容' })
      }
      return Promise.reject(new Error(`Unexpected url: ${url}`))
    })

    render(<LearningJournalPage />)
    await user.click(await screen.findByRole('button', { name: '编辑今日复盘' }))
    tiptapMockState.config?.onUpdate?.({ editor: { getHTML: () => '<p>今天完成了听力复习。</p>' } })
    await new Promise(resolve => window.setTimeout(resolve, 2100))

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        '/api/notes/journal',
        expect.objectContaining({ method: 'POST' }),
      )
    })
    await user.click(await screen.findByRole('button', { name: 'AI 润色' }))

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        '/api/notes/journal/polish',
        expect.objectContaining({ method: 'POST' }),
      )
    })

    const dialog = await screen.findByRole('dialog', { name: 'AI 润色预览' })
    expect(dialog).toHaveTextContent('确认润色结果后再应用到今天的日记正文。')
    expect(screen.getByRole('button', { name: '继续润色' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '拒绝' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '接受修改' })).toBeInTheDocument()
  }, 8000)

  it('shows feedback instead of silently ignoring polish on empty content', async () => {
    const alertSpy = vi.spyOn(window, 'alert')
    const user = userEvent.setup()
    apiFetchMock.mockImplementation((url: string) => {
      if (url === '/api/notes/journal/today') {
        return Promise.resolve({ entry: { ...todayEntry, content: '' } })
      }
      return Promise.reject(new Error(`Unexpected url: ${url}`))
    })

    render(<LearningJournalPage />)
    await user.click(await screen.findByRole('button', { name: '编辑今日复盘' }))
    await user.click(await screen.findByRole('button', { name: 'AI 润色' }))

    expect(alertSpy).toHaveBeenCalledWith('请先写一点内容再润色')
    expect(apiFetchMock).not.toHaveBeenCalledWith(
      '/api/notes/journal/polish',
      expect.anything(),
    )
  })
})
