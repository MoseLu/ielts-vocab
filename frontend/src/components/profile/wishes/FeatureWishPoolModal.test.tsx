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
      created_at: '2026-04-30T01:24:00',
      updated_at: '2026-04-30T01:24:00',
      can_edit: true,
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
      created_at: '2026-04-29T13:10:00',
      updated_at: '2026-04-29T13:10:00',
      can_edit: false,
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
    expect(cards[0].querySelector('.feature-wish-card__footer .feature-wish-card__edit')).not.toBeNull()
    expect(cards[1].querySelector('.feature-wish-card__footer .feature-wish-card__edit')).toBeNull()
  })

  it('expands a card inside the modal and uses the full image', async () => {
    const { baseElement } = render(<FeatureWishPoolModal onClose={vi.fn()} />)

    await screen.findByText('错题清单自动整理')
    fireEvent.click(screen.getByLabelText('展开愿望：错题清单自动整理'))

    expect(baseElement.querySelector('.feature-wish-detail')).not.toBeNull()
    const image = baseElement.querySelector('.feature-wish-detail__image') as HTMLImageElement
    expect(image.src).toBe('https://oss.example.com/full.png')
    expect(screen.getByLabelText('返回愿望列表')).toBeInTheDocument()
  })

  it('sends search text to the backend query', async () => {
    render(<FeatureWishPoolModal onClose={vi.fn()} />)
    await screen.findByText('错题清单自动整理')

    fireEvent.change(screen.getByPlaceholderText('搜索愿望名'), { target: { value: '口语' } })

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenLastCalledWith('/api/feature-wishes?search=%E5%8F%A3%E8%AF%AD')
    })
  })
})
