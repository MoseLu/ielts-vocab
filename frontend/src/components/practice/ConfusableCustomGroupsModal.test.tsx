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
      groupCount: 2,
      issues: [],
    })
  })

  it('merges multiline long groups when lines are separated by a blank line', () => {
    expect(
      parseConfusableCustomDraft('strick,\nstock,\nstruck,\nstriking,\nstring\n\naffect effect'),
    ).toEqual({
      groups: [
        ['strick', 'stock', 'struck', 'striking', 'string'],
        ['affect', 'effect'],
      ],
      groupCount: 2,
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
      expect(screen.getByText('3 个词 · 6 张卡片')).toBeInTheDocument()
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

  it('updates an existing custom group in edit mode', async () => {
    const onUpdated = vi.fn()

    apiFetchMock.mockResolvedValue({
      chapter: { id: 1001, title: '自定义易混组 01 · affect / effect / ...', word_count: 4, group_count: 1, is_custom: true },
      words: [
        { word: 'affect', phonetic: '/əˈfekt/', pos: 'v.', definition: '影响', group_key: 'custom-1001' },
        { word: 'effect', phonetic: '/ɪˈfekt/', pos: 'n.', definition: '效果', group_key: 'custom-1001' },
        { word: 'adapt', phonetic: '/əˈdæpt/', pos: 'v.', definition: '适应', group_key: 'custom-1001' },
        { word: 'adopt', phonetic: '/əˈdɒpt/', pos: 'v.', definition: '采用', group_key: 'custom-1001' },
      ],
    })

    render(
      <ConfusableCustomGroupsModal
        isOpen
        editChapter={{ id: 1001, title: '自定义易混组 01 · whether / weather', word_count: 2, is_custom: true }}
        initialWords={['whether', 'weather']}
        onClose={() => {}}
        onUpdated={onUpdated}
      />,
    )

    expect(screen.getByDisplayValue('whether, weather')).toBeInTheDocument()

    fireEvent.change(screen.getByRole('textbox'), {
      target: {
        value: 'affect, effect, adapt, adopt',
      },
    })

    fireEvent.click(screen.getByRole('button', { name: '保存并刷新当前组' }))

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        '/api/books/ielts_confusable_match/custom-chapters/1001',
        expect.objectContaining({ method: 'PUT' }),
      )
    })

    expect(onUpdated).toHaveBeenCalledWith(
      { id: 1001, title: '自定义易混组 01 · affect / effect / ...', word_count: 4, group_count: 1, is_custom: true },
      expect.arrayContaining([
        expect.objectContaining({ word: 'affect' }),
        expect.objectContaining({ word: 'adopt' }),
      ]),
    )
    expect(showToastMock).toHaveBeenCalledWith('已更新当前自定义易混组', 'success')
  })
})
