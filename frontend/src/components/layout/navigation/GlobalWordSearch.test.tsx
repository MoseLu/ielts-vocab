import React from 'react'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import GlobalWordSearch from './GlobalWordSearch'

const apiFetchMock = vi.fn()
const playExampleAudioMock = vi.fn()
const stopAudioMock = vi.fn()

vi.mock('../../../lib', async () => {
  const actual = await vi.importActual<typeof import('../../../lib')>('../../../lib')
  return {
    ...actual,
    apiFetch: (...args: unknown[]) => apiFetchMock(...args),
  }
})

vi.mock('../../practice/utils', () => ({
  playExampleAudio: (...args: unknown[]) => playExampleAudioMock(...args),
  stopAudio: (...args: unknown[]) => stopAudioMock(...args),
}))

const quitSearchResult = {
  query: 'quit',
  total: 2,
  results: [
    {
      word: 'quit',
      phonetic: '/kwɪt/',
      pos: 'v.',
      definition: '停止；离开',
      book_id: 'book-a',
      book_title: 'Book A',
      chapter_id: 2,
      chapter_title: 'Chapter 2',
      match_type: 'exact' as const,
      examples: [{ en: 'He decided to quit last year.', zh: '他决定去年戒掉。' }],
      listening_confusables: [{ word: 'quiet', phonetic: '/ˈkwaɪət/', pos: 'adj.', definition: '安静的' }],
    },
    {
      word: 'quits',
      phonetic: '/kwɪts/',
      pos: 'v.',
      definition: 'quit 的第三人称单数',
      book_id: 'book-a',
      book_title: 'Book A',
      match_type: 'prefix' as const,
    },
  ],
}

const quitWordDetails = {
  word: 'quit',
  phonetic: '/kwɪt/',
  pos: 'v.',
  definition: '停止；离开',
  root: {
    word: 'quit',
    normalized_word: 'quit',
    segments: [{ kind: '词根' as const, text: 'quit', meaning: '当前词形本身就是核心记忆单元' }],
    summary: '当前没有命中常见前后缀，可以直接把 quit 作为核心词形记忆。',
    source: 'generated',
    updated_at: null,
  },
  english: {
    word: 'quit',
    normalized_word: 'quit',
    entries: [
      { pos: 'v.', definition: 'to stop doing something' },
      { pos: 'v.', definition: 'to leave a job, school, or place' },
    ],
    source: 'llm',
    updated_at: null,
  },
  examples: [
    { en: 'She decided to quit her job before the exam season.', zh: '她决定在考试季前辞职。', source: 'llm', sort_order: 0 },
    { en: 'Many students quit the course when the workload became too heavy.', zh: '当课业负担太重时，很多学生退出了课程。', source: 'llm', sort_order: 1 },
  ],
  derivatives: [{
    word: 'quits',
    phonetic: '/kwɪts/',
    pos: 'v.',
    definition: '退出；辞职',
    relation_type: 'generated',
    source: 'catalog',
    sort_order: 0,
  }],
  note: {
    word: 'quit',
    content: '',
    updated_at: null,
  },
}

describe('GlobalWordSearch', () => {
  beforeEach(() => {
    apiFetchMock.mockReset()
    playExampleAudioMock.mockReset()
    stopAudioMock.mockReset()
    localStorage.clear()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('does not query the backend until the user explicitly submits', async () => {
    apiFetchMock.mockResolvedValue({ query: 'va', total: 0, results: [] })

    render(<GlobalWordSearch />)

    fireEvent.keyDown(window, { key: 'Q', shiftKey: true })

    const input = await screen.findByRole('searchbox', { name: '全局单词搜索' })
    fireEvent.change(input, { target: { value: 'va' } })

    await new Promise(resolve => window.setTimeout(resolve, 350))
    expect(apiFetchMock).not.toHaveBeenCalled()

    fireEvent.submit(input.closest('form') as HTMLFormElement)

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        '/api/books/search?q=va&limit=12',
        expect.objectContaining({ signal: expect.any(AbortSignal) }),
      )
    })
  })

  it('shows only the input and inline shortcut before submit', async () => {
    render(<GlobalWordSearch />)

    fireEvent.keyDown(window, { key: 'Q', shiftKey: true })

    await screen.findByRole('searchbox', { name: '全局单词搜索' })

    expect(screen.getByText('Shift + Q')).toBeInTheDocument()
    expect(screen.queryByText('输入英文、短语或中文释义开始搜索')).not.toBeInTheDocument()
    expect(screen.queryByText('输入完成后按 Enter 或点击搜索按钮提交')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '搜索单词' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '关闭搜索' })).not.toBeInTheDocument()
  })

  it('opens with Shift + Q and renders search results after submit', async () => {
    apiFetchMock.mockImplementation((url: string) => {
      if (url === '/api/books/search?q=quit&limit=12') {
        return Promise.resolve(quitSearchResult)
      }
      if (url === '/api/books/word-details?word=quit') {
        return Promise.resolve(quitWordDetails)
      }
      return Promise.resolve({ query: 'other', total: 0, results: [] })
    })

    const { container } = render(<GlobalWordSearch />)

    fireEvent.keyDown(window, { key: 'Q', shiftKey: true })

    const input = await screen.findByRole('searchbox', { name: '全局单词搜索' })
    await waitFor(() => {
      expect(input).toHaveFocus()
    })

    fireEvent.change(input, { target: { value: 'quit' } })
    fireEvent.submit(container.querySelector('.global-word-search-form') as HTMLFormElement)

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        '/api/books/search?q=quit&limit=12',
        expect.objectContaining({ signal: expect.any(AbortSignal) }),
      )
    })

    await screen.findByText('v. 停止；离开')

    expect(screen.getByText('/kwɪt/')).toBeInTheDocument()
    expect(screen.getByText('串记')).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: '例句' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: '英义' })).toBeInTheDocument()
    expect(screen.queryByRole('searchbox', { name: '全局单词搜索' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '搜索单词' })).not.toBeInTheDocument()
    expect(screen.queryByText('Book A')).not.toBeInTheDocument()
    expect(screen.queryByText('Chapter 2')).not.toBeInTheDocument()
    expect(screen.queryByText('共 2 条结果')).not.toBeInTheDocument()
  })

  it('accepts search results with empty definitions and shows a fallback label', async () => {
    apiFetchMock.mockImplementation((url: string) => {
      if (url === '/api/books/search?q=quit&limit=12') {
        return Promise.resolve({
          query: 'quit',
          total: 1,
          results: [{
            word: 'equity',
            phonetic: '',
            pos: 'noun',
            definition: '',
            book_id: 'book-b',
            book_title: 'Book B',
            match_type: 'example' as const,
            examples: [{ en: 'He decided to quit last year.', zh: '他去年辞职了。' }],
          }],
        })
      }
      if (url === '/api/books/word-details?word=equity') {
        return Promise.resolve({
          word: 'equity',
          phonetic: '',
          pos: 'noun',
          definition: '',
          root: {
            word: 'equity',
            normalized_word: 'equity',
            segments: [{ kind: '词根' as const, text: 'equi', meaning: '建议把这部分当作核心词形来记' }],
            summary: '可以按“equi + ty”来拆分记忆。',
            source: 'generated',
            updated_at: null,
          },
          english: {
            word: 'equity',
            normalized_word: 'equity',
            entries: [],
            source: 'none',
            updated_at: null,
          },
          examples: [],
          derivatives: [],
          note: { word: 'equity', content: '', updated_at: null },
        })
      }
      return Promise.resolve({ query: 'other', total: 0, results: [] })
    })

    const { container } = render(<GlobalWordSearch />)

    fireEvent.keyDown(window, { key: 'Q', shiftKey: true })

    const input = await screen.findByRole('searchbox', { name: '全局单词搜索' })
    fireEvent.change(input, { target: { value: 'quit' } })
    fireEvent.submit(container.querySelector('.global-word-search-form') as HTMLFormElement)

    await screen.findByText('noun 暂无释义')
    expect(screen.queryByText('搜索结果格式错误')).not.toBeInTheDocument()
  })

  it('prefers detail phonetic when the selected search result phonetic is empty', async () => {
    apiFetchMock.mockImplementation((url: string) => {
      if (url === '/api/books/search?q=quit&limit=12') {
        return Promise.resolve({
          query: 'quit',
          total: 1,
          results: [{
            ...quitSearchResult.results[0],
            phonetic: '',
          }],
        })
      }
      if (url === '/api/books/word-details?word=quit') {
        return Promise.resolve(quitWordDetails)
      }
      return Promise.resolve({ query: 'other', total: 0, results: [] })
    })

    const { container } = render(<GlobalWordSearch />)

    fireEvent.keyDown(window, { key: 'Q', shiftKey: true })

    const input = await screen.findByRole('searchbox', { name: '全局单词搜索' })
    fireEvent.change(input, { target: { value: 'quit' } })
    fireEvent.submit(container.querySelector('.global-word-search-form') as HTMLFormElement)

    await screen.findByText('/kwɪt/')
  })

  it('loads backend derivatives and saves notes through the api', async () => {
    apiFetchMock.mockImplementation((url: string, options?: RequestInit) => {
      if (url === '/api/books/search?q=quit&limit=12') {
        return Promise.resolve(quitSearchResult)
      }
      if (url === '/api/books/word-details?word=quit') {
        return Promise.resolve(quitWordDetails)
      }
      if (url === '/api/books/word-details/note' && options?.method === 'PUT') {
        return Promise.resolve({
          note: {
            word: 'quit',
            content: '记住 quit 和 quiet 的区别',
            updated_at: '2026-04-05T10:00:00+00:00',
          },
        })
      }
      return Promise.resolve({ query: 'other', total: 0, results: [] })
    })

    const { container } = render(<GlobalWordSearch />)

    fireEvent.keyDown(window, { key: 'Q', shiftKey: true })
    const input = await screen.findByRole('searchbox', { name: '全局单词搜索' })
    fireEvent.change(input, { target: { value: 'quit' } })
    fireEvent.submit(container.querySelector('.global-word-search-form') as HTMLFormElement)

    await screen.findByText('v. 停止；离开')
    await screen.findByRole('button', { name: '朗读例句 1' })

    fireEvent.click(screen.getByRole('tab', { name: '派生' }))
    await screen.findByText('v. · 退出；辞职')

    fireEvent.click(screen.getByRole('tab', { name: '英义' }))
    await screen.findByText('to stop doing something')

    fireEvent.click(screen.getByRole('tab', { name: '笔记' }))
    const textarea = screen.getByPlaceholderText('输入笔记内容')
    fireEvent.change(textarea, { target: { value: '记住 quit 和 quiet 的区别' } })

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        '/api/books/word-details/note',
        expect.objectContaining({
          method: 'PUT',
          body: JSON.stringify({
            word: 'quit',
            content: '记住 quit 和 quiet 的区别',
          }),
        }),
      )
    })

    expect(screen.getByText('已保存到账号')).toBeInTheDocument()
  })

  it('plays example audio from the examples tab with the stored playback settings', async () => {
    localStorage.setItem('app_settings', JSON.stringify({
      playbackSpeed: '1.25',
      volume: '80',
    }))
    apiFetchMock.mockImplementation((url: string) => {
      if (url === '/api/books/search?q=quit&limit=12') {
        return Promise.resolve(quitSearchResult)
      }
      if (url === '/api/books/word-details?word=quit') {
        return Promise.resolve(quitWordDetails)
      }
      return Promise.resolve({ query: 'other', total: 0, results: [] })
    })

    const { container } = render(<GlobalWordSearch />)

    fireEvent.keyDown(window, { key: 'Q', shiftKey: true })

    const input = await screen.findByRole('searchbox', { name: '全局单词搜索' })
    fireEvent.change(input, { target: { value: 'quit' } })
    fireEvent.submit(container.querySelector('.global-word-search-form') as HTMLFormElement)

    await screen.findByText('她决定在考试季前辞职。')

    fireEvent.click(screen.getByRole('button', { name: '朗读例句 1' }))

    expect(playExampleAudioMock).toHaveBeenCalledWith(
      'She decided to quit her job before the exam season.',
      'quit',
      {
        playbackSpeed: '1.25',
        volume: '80',
      },
    )
  })

  it('plays the first visible example audio when Alt is pressed', async () => {
    localStorage.setItem('app_settings', JSON.stringify({
      playbackSpeed: '1.25',
      volume: '80',
    }))
    apiFetchMock.mockImplementation((url: string) => {
      if (url === '/api/books/search?q=quit&limit=12') {
        return Promise.resolve(quitSearchResult)
      }
      if (url === '/api/books/word-details?word=quit') {
        return Promise.resolve(quitWordDetails)
      }
      return Promise.resolve({ query: 'other', total: 0, results: [] })
    })

    const { container } = render(<GlobalWordSearch />)

    fireEvent.keyDown(window, { key: 'Q', shiftKey: true })

    const input = await screen.findByRole('searchbox', { name: '全局单词搜索' })
    fireEvent.change(input, { target: { value: 'quit' } })
    fireEvent.submit(container.querySelector('.global-word-search-form') as HTMLFormElement)

    await screen.findByText('她决定在考试季前辞职。')

    fireEvent.keyDown(window, { key: 'Alt', code: 'AltLeft', altKey: true })

    expect(playExampleAudioMock).toHaveBeenCalledWith(
      'She decided to quit her job before the exam season.',
      'quit',
      {
        playbackSpeed: '1.25',
        volume: '80',
      },
    )
  })
})
