import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import PlanModal from './PlanModal'

describe('PlanModal', () => {
  it('starts regular practice without showing the game entry selector', async () => {
    const user = userEvent.setup()
    const onStart = vi.fn()

    render(
      <PlanModal
        book={{ id: 'book-1', title: 'Test Book', word_count: 100 }}
        progress={{ current_index: 20 }}
        onClose={() => {}}
        onStart={onStart}
      />,
    )

    expect(screen.queryByRole('tablist', { name: '学习入口' })).not.toBeInTheDocument()
    expect(screen.queryByText('游戏闯关')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: '继续学习' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '继续闯关' })).not.toBeInTheDocument()

    await user.click(screen.getByText('10 词/天'))

    expect(onStart).toHaveBeenCalledWith({
      bookId: 'book-1',
      dailyCount: 10,
      totalDays: 8,
      startIndex: 20,
    })
    expect(onStart.mock.calls[0]).toHaveLength(1)
  })
})
