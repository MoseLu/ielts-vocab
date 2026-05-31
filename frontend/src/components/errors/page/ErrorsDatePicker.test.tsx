import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { ErrorsDatePicker } from './ErrorsDatePicker'

describe('ErrorsDatePicker', () => {
  it('opens a calendar popup and writes the picked date as yyyy-mm-dd', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-05-15T08:00:00.000Z'))
    const onChange = vi.fn()

    render(<ErrorsDatePicker ariaLabel="起始日期" value="" onChange={onChange} />)

    fireEvent.focus(screen.getByLabelText('起始日期'))
    expect(screen.getByRole('dialog', { name: '起始日期日历' })).toBeInTheDocument()
    expect(screen.getByText('2026 年 5 月')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: '选择日期 2026-05-15' }))

    expect(onChange).toHaveBeenCalledWith('2026-05-15')
    vi.useRealTimers()
  })

  it('lets learners move between months before selecting a date', () => {
    const onChange = vi.fn()

    render(<ErrorsDatePicker ariaLabel="结束日期" value="2026-04-07" onChange={onChange} />)

    fireEvent.focus(screen.getByLabelText('结束日期'))
    expect(screen.getByText('2026 年 4 月')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: '下个月' }))
    expect(screen.getByText('2026 年 5 月')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: '选择日期 2026-05-01' }))
    expect(onChange).toHaveBeenCalledWith('2026-05-01')
  })
})
