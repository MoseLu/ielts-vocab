import React from 'react'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { vi } from 'vitest'
import ConfusableCustomGroupsModal, {
  parseConfusableCustomDraft,
} from './ConfusableCustomGroupsModal'

const apiFetchMock = vi.fn()
const showToastMock = vi.fn()

vi.mock('../../contexts', () => ({
  useToast: () => ({ showToast: showToastMock }),
}))

vi.mock('../../lib', async () => {
  const actual = await vi.importActual<typeof import('../../lib')>('../../lib')
  return {
    ...actual,
    apiFetch: (...args: unknown[]) => apiFetchMock(...args),
  }
})

describe('ConfusableCustomGroupsModal', () => {
  beforeEach(() => {
    apiFetchMock.mockReset()
    showToastMock.mockReset()
  })

  it('parses one group per line and deduplicates repeated words', () => {
    expect(parseConfusableCustomDraft('collect college collect\nAffect, effect')).toEqual({
      groups: [
        ['collect', 'college'],
        ['affect', 'effect'],
      ],
      lineCount: 2,
      issues: [],
    })
  })

  it('submits parsed groups and returns created chapters', async () => {
    const onCreated = vi.fn()

    apiFetchMock.mockResolvedValue({
      created_count: 2,
      created_chapters: [
        { id: 1001, title: '自定义易混组 01 · collect / college', word_count: 2, is_custom: true },
        { id: 1002, title: '自定义易混组 02 · affect / effect', word_count: 2, is_custom: true },
      ],
    })

    render(
      <ConfusableCustomGroupsModal
        isOpen
        onClose={() => {}}
        onCreated={onCreated}
      />,
    )

    fireEvent.change(screen.getByRole('textbox'), {
      target: {
        value: 'collect college colleague\naffect, effect',
      },
    })

    await waitFor(() => {
      expect(screen.getByText('collect')).toBeInTheDocument()
      expect(screen.getByText('affect')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByRole('button', { name: '创建并开始练习' }))

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        '/api/books/ielts_confusable_match/custom-chapters',
        expect.objectContaining({
          method: 'POST',
        }),
      )
    })

    expect(apiFetchMock.mock.calls[0][1].body).toContain('"groups":[["collect","college","colleague"],["affect","effect"]]')
    expect(onCreated).toHaveBeenCalledWith([
      { id: 1001, title: '自定义易混组 01 · collect / college', word_count: 2, is_custom: true },
      { id: 1002, title: '自定义易混组 02 · affect / effect', word_count: 2, is_custom: true },
    ])
    expect(showToastMock).toHaveBeenCalledWith('已创建 2 组自定义易混词', 'success')
  })

  it('blocks submit when a line contains fewer than two words', async () => {
    render(
      <ConfusableCustomGroupsModal
        isOpen
        onClose={() => {}}
      />,
    )

    fireEvent.change(screen.getByRole('textbox'), {
      target: {
        value: 'collect',
      },
    })

    fireEvent.click(screen.getByRole('button', { name: '创建并开始练习' }))

    expect(apiFetchMock).not.toHaveBeenCalled()
    expect(await screen.findByRole('alert')).toHaveTextContent('第 1 组至少需要 2 个不同单词')
  })
})
