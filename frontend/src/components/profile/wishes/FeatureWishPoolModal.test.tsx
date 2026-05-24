import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import FeatureWishPoolModal from './FeatureWishPoolModal'

const apiFetchMock = vi.fn()

vi.mock('../../../lib', () => ({
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
}))

const wishesResponse = {
  items: [
    {
      id: 1,
      user_id: 7,
      username: 'admin',
      title: '错题清单自动整理',
      content: '练习结束后生成错词复盘清单',
      status: 'open',
      created_at: '2026-04-30T01:24:00',
      updated_at: '2026-04-30T01:24:00',
      can_edit: true,
      can_delete: true,
      can_update_status: true,
      images: [{
        id: 10,
        thumbnail_url: 'https://oss.example.com/thumb.png',
        full_url: 'https://oss.example.com/full.png',
        original_filename: 'wish.png',
      }],
    },
    {
      id: 2,
      user_id: 8,
      username: 'learner',
      title: '口语主题筛选',
      content: '按口语场景筛选词汇',
      status: 'done',
      created_at: '2026-04-29T13:10:00',
      updated_at: '2026-04-29T13:10:00',
      can_edit: false,
      can_delete: false,
      can_update_status: false,
      images: [],
    },
  ],
  total: 2,
}

describe('FeatureWishPoolModal', () => {
  beforeEach(() => {
    apiFetchMock.mockReset()
    apiFetchMock.mockResolvedValue(wishesResponse)
  })

  it('renders element-plus-style wish cards with top images and icon actions', async () => {
    const { baseElement } = render(<FeatureWishPoolModal onClose={vi.fn()} />)

    await screen.findByText('错题清单自动整理')

    const cards = baseElement.querySelectorAll('.feature-wish-card')
    expect(cards).toHaveLength(2)
    expect(cards[0].querySelector('.feature-wish-card__media img')).not.toBeNull()
    expect(cards[0].querySelector('.feature-wish-card__expand')).not.toBeNull()
    expect(cards[0].querySelector('.feature-wish-status-badge')?.textContent).toBe('待评估')
    expect(cards[1].classList.contains('feature-wish-card--done')).toBe(true)
    expect(cards[0].querySelector('.feature-wish-card__footer .feature-wish-card__edit')).not.toBeNull()
    expect(cards[1].querySelector('.feature-wish-card__footer .feature-wish-card__edit')).toBeNull()
  })

  it('expands a card inside the modal and uses the full image', async () => {
    const { baseElement } = render(<FeatureWishPoolModal onClose={vi.fn()} />)

    await screen.findByText('错题清单自动整理')
    fireEvent.click(screen.getByLabelText('展开 bug：错题清单自动整理'))

    expect(baseElement.querySelector('.feature-wish-detail')).not.toBeNull()
    const image = baseElement.querySelector('.feature-wish-detail__image') as HTMLImageElement
    expect(image.src).toBe('https://oss.example.com/full.png')
    expect(screen.getByLabelText('返回 bug 列表')).toBeInTheDocument()
  })

  it('sends search text to the backend query', async () => {
    render(<FeatureWishPoolModal onClose={vi.fn()} />)
    await screen.findByText('错题清单自动整理')

    fireEvent.change(screen.getByPlaceholderText('搜索 bug 标题'), { target: { value: '口语' } })

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenLastCalledWith('/api/feature-wishes?search=%E5%8F%A3%E8%AF%AD')
    })
  })

  it('lets admins delete a wish through the built-in confirm dialog and refreshes the list', async () => {
    apiFetchMock
      .mockResolvedValueOnce(wishesResponse)
      .mockResolvedValueOnce({ message: 'bug 已删除' })
      .mockResolvedValueOnce({ items: [wishesResponse.items[1]], total: 1 })

    render(<FeatureWishPoolModal onClose={vi.fn()} />)
    await screen.findByText('错题清单自动整理')

    fireEvent.click(screen.getByLabelText('删除 bug：错题清单自动整理'))

    expect(screen.getByRole('dialog', { name: '确认删除 bug' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: '删除' }))

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith('/api/feature-wishes/1', { method: 'DELETE' })
    })
    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenLastCalledWith('/api/feature-wishes')
    })
  })

  it('lets admins update a wish status to completed from the card', async () => {
    const doneWish = { ...wishesResponse.items[0], status: 'done' }
    apiFetchMock
      .mockResolvedValueOnce(wishesResponse)
      .mockResolvedValueOnce({ message: 'bug 状态已更新', wish: doneWish })

    const { baseElement } = render(<FeatureWishPoolModal onClose={vi.fn()} />)
    await screen.findByText('错题清单自动整理')

    fireEvent.change(screen.getByLabelText('设置 bug 状态：错题清单自动整理'), { target: { value: 'done' } })

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith('/api/feature-wishes/1/status', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: 'done' }),
      })
    })
    await waitFor(() => {
      const firstCard = baseElement.querySelector('.feature-wish-card') as HTMLElement
      expect(firstCard.classList.contains('feature-wish-card--done')).toBe(true)
    })
  })

  it('opens the create form with an initial screenshot already attached', async () => {
    const screenshot = new File(['shot'], 'bug-screenshot-initial.png', { type: 'image/png' })

    render(<FeatureWishPoolModal initialDraftFiles={[screenshot]} onClose={vi.fn()} />)
    await screen.findByText('错题清单自动整理')

    expect(screen.getByText('bug-screenshot-initial.png')).toBeInTheDocument()
    fireEvent.change(screen.getByPlaceholderText('bug 标题'), { target: { value: '全局截图问题' } })
    fireEvent.change(screen.getByPlaceholderText('bug 内容'), { target: { value: '快捷键截图后提交' } })
    fireEvent.click(screen.getByRole('button', { name: '保存' }))

    await waitFor(() => {
      const submitCall = apiFetchMock.mock.calls.find(([url, options]) => {
        return url === '/api/feature-wishes' && (options as { method?: string } | undefined)?.method === 'POST'
      })
      const body = submitCall?.[1]?.body as FormData
      expect(body.getAll('images')).toEqual([screenshot])
    })
  })
})
