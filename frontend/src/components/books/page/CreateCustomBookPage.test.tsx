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

function renderPage() {
  return render(
    <MemoryRouter>
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
})
