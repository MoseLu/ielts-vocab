import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { ToastProvider } from '../../../contexts'
import CreateCustomBookPage from './CreateCustomBookPage'

const navigateMock = vi.fn()
const apiFetchMock = vi.fn()

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return {
    ...actual,
    useNavigate: () => navigateMock,
  }
})

vi.mock('../../../lib', async () => {
  const actual = await vi.importActual<typeof import('../../../lib')>('../../../lib')
  return {
    ...actual,
    apiFetch: (...args: unknown[]) => apiFetchMock(...args),
  }
})

function renderPage(initialEntries: string[] = ['/books/create']) {
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <ToastProvider>
        <CreateCustomBookPage />
      </ToastProvider>
    </MemoryRouter>,
  )
}

describe('CreateCustomBookPage', () => {
  beforeEach(() => {
    navigateMock.mockReset()
    apiFetchMock.mockReset()
  })

  it('renders defaults and updates chapter word count from textarea content', async () => {
    const user = userEvent.setup()
    renderPage()

    expect(screen.getByRole('heading', { name: '创建一本可立即学习的词书' })).toBeInTheDocument()
    expect(screen.getByDisplayValue('我的自定义词书')).toBeInTheDocument()

    await user.type(screen.getByLabelText('单词内容'), 'abandon{enter}ability')

    expect(screen.getByText('2 个词条')).toBeInTheDocument()
    expect(screen.getByText('2 个词')).toBeInTheDocument()
  })

  it('adds chapters and collapses cards in reorder mode with fallback move buttons', async () => {
    const user = userEvent.setup()
    renderPage()

    await user.click(screen.getByRole('button', { name: '添加章节' }))
    await user.click(screen.getByRole('button', { name: '调整排序' }))

    expect(screen.queryByLabelText('单词内容')).not.toBeInTheDocument()
    expect(screen.getAllByText('拖拽')).toHaveLength(2)

    await user.click(screen.getAllByRole('button', { name: '下移' })[0])
    expect(screen.getAllByText(/第\d章/)[0]).toHaveTextContent('第2章')
  })

  it('saves a valid manual book then adds it to my books', async () => {
    const user = userEvent.setup()
    apiFetchMock
      .mockResolvedValueOnce({ bookId: 'custom_1', book: { id: 'custom_1', incomplete_word_count: 1 } })
      .mockResolvedValueOnce({ book_id: 'custom_1' })

    renderPage()

    await user.type(screen.getByLabelText('单词内容'), 'meticulous')
    await user.click(screen.getByRole('button', { name: '保存词书' }))

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith('/api/books/custom-books', expect.objectContaining({
        method: 'POST',
      }))
    })
    expect(apiFetchMock).toHaveBeenCalledWith('/api/books/my', expect.objectContaining({
      method: 'POST',
      body: JSON.stringify({ book_id: 'custom_1' }),
    }))
    expect(navigateMock).toHaveBeenCalledWith('/plan')
  })

  it('returns to the study center when canceled', async () => {
    const user = userEvent.setup()
    renderPage()

    await user.click(screen.getByRole('button', { name: '取消' }))

    expect(navigateMock).toHaveBeenCalledWith('/plan')
  })

  it('loads an existing custom book and saves added chapters through the update endpoint', async () => {
    const user = userEvent.setup()
    apiFetchMock
      .mockResolvedValueOnce({
        id: 'custom_9',
        title: '听力补充词书',
        word_count: 42,
        education_stage: 'abroad',
        exam_type: 'ielts',
        ielts_skill: 'listening',
        share_enabled: false,
        chapter_word_target: 30,
        chapters: [
          { id: 'custom_9_1', title: '第1章', words: [{ id: 1, word: 'abandon' }] },
          { id: 'custom_9_2', title: '第2章', words: [{ id: 2, word: 'ability' }] },
        ],
      })
      .mockResolvedValueOnce({
        bookId: 'custom_9',
        book: { id: 'custom_9', incomplete_word_count: 0 },
      })

    renderPage(['/books/create?bookId=custom_9'])

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: '编辑自定义词书' })).toBeInTheDocument()
    })
    const titleInput = await screen.findByDisplayValue('听力补充词书')
    expect(titleInput).toBeDisabled()
    expect(screen.getByDisplayValue('abandon')).toBeInTheDocument()
    expect(screen.getByDisplayValue('ability')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: '添加章节' }))
    expect(screen.getByLabelText('章节 3')).toBeInTheDocument()

    await user.type(screen.getAllByLabelText('单词内容')[2], 'meticulous')
    await user.click(screen.getByRole('button', { name: '保存词书修改' }))

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith('/api/books/custom-books/custom_9', expect.objectContaining({
        method: 'PUT',
      }))
    })
    expect(apiFetchMock.mock.calls[1][1].body).toContain('abandon')
    expect(apiFetchMock.mock.calls[1][1].body).toContain('meticulous')
    expect(apiFetchMock).not.toHaveBeenCalledWith('/api/books/my', expect.anything())
    expect(navigateMock).toHaveBeenCalledWith('/books')
  })

  it('loads existing custom book chapters for editing and saves changes through the update endpoint', async () => {
    const user = userEvent.setup()
    apiFetchMock
      .mockResolvedValueOnce({
        id: 'custom_9',
        title: '听力补充词书',
        word_count: 2,
        education_stage: 'abroad',
        exam_type: 'ielts',
        ielts_skill: 'listening',
        share_enabled: false,
        chapter_word_target: 30,
        chapters: [{
          id: 'custom_9_1',
          title: '旧章节',
          words: [{ id: 1, word: 'abandon' }],
        }],
      })
      .mockResolvedValueOnce({
        bookId: 'custom_9',
        book: { id: 'custom_9', incomplete_word_count: 0 },
      })

    renderPage(['/books/create?bookId=custom_9'])

    expect(await screen.findByDisplayValue('旧章节')).toBeInTheDocument()
    const wordInput = await screen.findByDisplayValue('abandon')
    await user.clear(wordInput)
    await user.type(wordInput, 'coherent')
    await user.click(screen.getByRole('button', { name: '保存词书修改' }))

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith('/api/books/custom-books/custom_9', expect.objectContaining({
        method: 'PUT',
      }))
    })
    expect(apiFetchMock.mock.calls[1][1].body).toContain('coherent')
    expect(navigateMock).toHaveBeenCalledWith('/books')
  })
})
