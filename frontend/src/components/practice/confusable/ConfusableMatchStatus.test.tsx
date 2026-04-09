import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { ConfusableMatchCompletedState } from './ConfusableMatchStatus'

describe('ConfusableMatchCompletedState', () => {
  it('renders the shared round summary layout', () => {
    render(
      <ConfusableMatchCompletedState
        chapterTitle="Chapter 3"
        correctCount={9}
        wrongCount={3}
        onReplay={vi.fn()}
        onBack={vi.fn()}
      />,
    )

    expect(screen.getByText('本轮完成')).toBeInTheDocument()
    expect(screen.getByText('Chapter 3')).toBeInTheDocument()
    expect(screen.getByText('75%')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '再来一轮' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '返回词书' })).toBeInTheDocument()
  })
})
