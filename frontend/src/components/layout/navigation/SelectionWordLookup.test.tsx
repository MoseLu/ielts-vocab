import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  MemoryRouter,
  Route,
  Routes,
  useNavigate,
  type NavigateFunction,
} from 'react-router-dom'
import SelectionWordLookup from './SelectionWordLookup'

const { openGlobalWordSearchMock, useAuthMock, useFavoriteWordsMock, useToastMock } = vi.hoisted(() => ({
  openGlobalWordSearchMock: vi.fn(),
  useAuthMock: vi.fn(() => ({ user: { id: 1, username: 'admin' } })),
  useFavoriteWordsMock: vi.fn(() => ({
    isFavorite: () => false,
    isPending: () => false,
    toggleFavorite: vi.fn(),
  })),
  useToastMock: vi.fn(() => ({ showToast: vi.fn() })),
}))

const apiFetchMock = vi.fn()
const playWordAudioMock = vi.fn()
const stopAudioMock = vi.fn()

vi.mock('../../../lib', async () => {
  const actual = await vi.importActual<typeof import('../../../lib')>('../../../lib')
  return {
    ...actual,
    apiFetch: (...args: unknown[]) => apiFetchMock(...args),
  }
})

vi.mock('../../../contexts', () => ({
  useAuth: () => useAuthMock(),
  useToast: () => useToastMock(),
}))

vi.mock('../../../features/vocabulary/hooks', () => ({
  useFavoriteWords: (...args: unknown[]) => useFavoriteWordsMock(...args),
}))

vi.mock('../../practice/utils.audio', () => ({
  playWordAudio: (...args: unknown[]) => playWordAudioMock(...args),
  stopAudio: (...args: unknown[]) => stopAudioMock(...args),
}))

vi.mock('./globalWordSearchEvents', () => ({
  GLOBAL_WORD_SEARCH_OPEN_EVENT: 'global-word-search:open',
  openGlobalWordSearch: (...args: unknown[]) => openGlobalWordSearchMock(...args),
}))

type MockSelectionState = {
  anchorNode: Node | null
  focusNode: Node | null
  isCollapsed: boolean
  rangeCount: number
  rect: DOMRect
  text: string
}

const baseStyles = readFileSync(resolve(process.cwd(), 'src/styles/base.tokens.scss'), 'utf-8')
const readRootLayerToken = (tokenName: string) => {
  const escapedName = tokenName.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const match = baseStyles.match(new RegExp(`${escapedName}:\\s*(\\d+)`, 'u'))
  return Number(match?.[1] ?? 0)
}

const quietSearchResult = {
  query: 'quiet',
  total: 1,
  results: [{
    word: 'quiet',
    phonetic: '',
    pos: 'adj.',
    definition: '安静的',
    book_id: 'book-a',
    book_title: 'Book A',
    chapter_id: 2,
    chapter_title: 'Chapter 2',
    match_type: 'exact' as const,
    examples: [{ en: 'Please keep quiet in the library.', zh: '在图书馆请保持安静。' }],
  }],
}

const quietWordDetails = {
  word: 'quiet',
  phonetic: '/ˈkwaɪət/',
  pos: 'adj.',
  definition: '安静的',
  root: {
    word: 'quiet',
    normalized_word: 'quiet',
    segments: [{ kind: '词根' as const, text: 'qui', meaning: '静' }],
    summary: 'quiet 可以直接按词形记忆。',
    source: 'generated',
    updated_at: null,
  },
  english: {
    word: 'quiet',
    normalized_word: 'quiet',
    entries: [{ pos: 'adj.', definition: 'making very little noise' }],
    source: 'llm',
    updated_at: null,
  },
  examples: [{
    en: 'The room stayed quiet after the bell rang.',
    zh: '铃响后房间依旧安静。',
    source: 'llm',
    sort_order: 0,
  }],
  derivatives: [],
  note: {
    word: 'quiet',
    content: '',
    updated_at: null,
  },
}

let selectionState: MockSelectionState
let navigateRef: NavigateFunction | null = null

function NavigationController() {
  navigateRef = useNavigate()
  return null
}

function LookupRoute() {
  return (
    <>
      <NavigationController />
      <SelectionWordLookup />
      <p data-testid="selectable">quiet</p>
      <div className="global-word-search-overlay">
        <div className="global-word-search-panel global-word-search-panel--with-result">
          <p data-testid="overlay-selectable">Please keep quiet in the library.</p>
        </div>
      </div>
      <input aria-label="editable" defaultValue="quiet" />
    </>
  )
}

function BooksRoute() {
  return (
    <>
      <NavigationController />
      <SelectionWordLookup />
      <p>Books page</p>
    </>
  )
}

function renderLookup() {
  return render(
    <MemoryRouter initialEntries={['/plan']}>
      <Routes>
        <Route path="/plan" element={<LookupRoute />} />
        <Route path="/books" element={<BooksRoute />} />
      </Routes>
    </MemoryRouter>,
  )
}

function mockSelection(target: Node, text: string, rect = new DOMRect(120, 80, 84, 24)) {
  selectionState = {
    text,
    rect,
    rangeCount: text ? 1 : 0,
    isCollapsed: !text,
    anchorNode: target,
    focusNode: target,
  }
}

describe('SelectionWordLookup', () => {
  beforeEach(() => {
    apiFetchMock.mockReset()
    openGlobalWordSearchMock.mockReset()
    playWordAudioMock.mockReset()
    stopAudioMock.mockReset()
    useAuthMock.mockReset()
    useFavoriteWordsMock.mockReset()
    useToastMock.mockReset()
    useAuthMock.mockReturnValue({ user: { id: 1, username: 'admin' } })
    useToastMock.mockReturnValue({ showToast: vi.fn() })
    useFavoriteWordsMock.mockReturnValue({
      isFavorite: () => false,
      isPending: () => false,
      toggleFavorite: vi.fn(),
    })
    selectionState = {
      text: '',
      rect: new DOMRect(0, 0, 0, 0),
      rangeCount: 0,
      isCollapsed: true,
      anchorNode: null,
      focusNode: null,
    }
    navigateRef = null
    vi.spyOn(document, 'getSelection').mockImplementation(() => ({
      anchorNode: selectionState.anchorNode,
      focusNode: selectionState.focusNode,
      isCollapsed: selectionState.isCollapsed,
      rangeCount: selectionState.rangeCount,
      toString: () => selectionState.text,
      getRangeAt: () => ({
        getBoundingClientRect: () => selectionState.rect,
      }),
    }) as unknown as Selection)
    localStorage.clear()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('keeps the selection lookup layer between the header and the global search overlay', () => {
    expect(readRootLayerToken('--layer-selection-lookup')).toBeGreaterThan(
      readRootLayerToken('--layer-header'),
    )
    expect(readRootLayerToken('--layer-selection-lookup')).toBeLessThan(
      readRootLayerToken('--layer-global-search'),
    )
  })

  it('opens a lightweight lookup card for an exact selected word', async () => {
    apiFetchMock.mockImplementation((url: string) => {
      if (url === '/api/books/search?q=quiet&limit=1') {
        return Promise.resolve(quietSearchResult)
      }
      if (url === '/api/books/word-details?word=quiet') {
        return Promise.resolve(quietWordDetails)
      }
      throw new Error(`Unexpected request: ${url}`)
    })

    renderLookup()
    const selectable = screen.getByTestId('selectable')
    mockSelection(selectable.firstChild as Text, 'quiet')

    fireEvent.pointerUp(selectable, { pointerType: 'mouse' })

    const dialog = await screen.findByRole('dialog', { name: '划词词典卡片：quiet' })
    expect(dialog).toHaveAttribute('data-detail-status', 'ready')
    expect(apiFetchMock).toHaveBeenCalledWith(
      '/api/books/search?q=quiet&limit=1',
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    )
    expect(apiFetchMock).toHaveBeenCalledWith(
      '/api/books/word-details?word=quiet',
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    )
    expect(screen.getByText('/ˈkwaɪət/')).toBeInTheDocument()
    expect(screen.getByText('Book A · Chapter 2')).toBeInTheDocument()
    expect(screen.getByText('The room stayed quiet after the bell rang.')).toBeInTheDocument()
    expect(screen.getByText('铃响后房间依旧安静。')).toBeInTheDocument()
  })

  it('supports lookup for words selected inside the global search overlay content', async () => {
    apiFetchMock.mockImplementation((url: string) => {
      if (url === '/api/books/search?q=quiet&limit=1') {
        return Promise.resolve(quietSearchResult)
      }
      if (url === '/api/books/word-details?word=quiet') {
        return Promise.resolve(quietWordDetails)
      }
      throw new Error(`Unexpected request: ${url}`)
    })

    renderLookup()
    const selectable = screen.getByTestId('overlay-selectable')
    mockSelection(selectable.firstChild as Text, 'quiet')

    fireEvent.pointerUp(selectable, { pointerType: 'mouse' })

    const dialog = await screen.findByRole('dialog', { name: '划词词典卡片：quiet' })
    expect(dialog).toHaveAttribute('data-context', 'global-search')
    expect(dialog.className).toContain('selection-word-lookup--global-search')
    expect(dialog).toHaveTextContent('adj. 安静的')
  })

  it('ignores multi-word selections and editable targets', async () => {
    apiFetchMock.mockResolvedValue(quietSearchResult)
    renderLookup()

    const selectable = screen.getByTestId('selectable')
    mockSelection(selectable.firstChild as Text, 'quiet mind')
    fireEvent.pointerUp(selectable, { pointerType: 'mouse' })

    await waitFor(() => {
      expect(apiFetchMock).not.toHaveBeenCalled()
    })

    const editable = screen.getByRole('textbox', { name: 'editable' })
    mockSelection(editable, 'quiet')
    fireEvent.pointerUp(editable, { pointerType: 'mouse' })

    await waitFor(() => {
      expect(apiFetchMock).not.toHaveBeenCalled()
      expect(screen.queryByRole('dialog', { name: '划词词典卡片：quiet' })).not.toBeInTheDocument()
    })
  })

  it('does not open a card when the first search result is only a prefix match', async () => {
    apiFetchMock.mockResolvedValue({
      query: 'quiet',
      total: 1,
      results: [{
        ...quietSearchResult.results[0],
        word: 'quietly',
        match_type: 'prefix' as const,
      }],
    })

    renderLookup()
    const selectable = screen.getByTestId('selectable')
    mockSelection(selectable.firstChild as Text, 'quiet')
    fireEvent.pointerUp(selectable, { pointerType: 'mouse' })

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        '/api/books/search?q=quiet&limit=1',
        expect.objectContaining({ signal: expect.any(AbortSignal) }),
      )
      expect(screen.queryByRole('dialog', { name: '划词词典卡片：quiet' })).not.toBeInTheDocument()
    })
  })

  it('aborts the previous lookup when a new selection replaces it', async () => {
    let firstSignal: AbortSignal | undefined
    apiFetchMock.mockImplementation((url: string, options?: RequestInit) => {
      if (url === '/api/books/search?q=quiet&limit=1') {
        firstSignal = options?.signal as AbortSignal
        return new Promise((_resolve, reject) => {
          options?.signal?.addEventListener('abort', () => {
            reject(new DOMException('Aborted', 'AbortError'))
          }, { once: true })
        })
      }
      if (url === '/api/books/search?q=quit&limit=1') {
        return Promise.resolve({
          query: 'quit',
          total: 1,
          results: [{
            ...quietSearchResult.results[0],
            word: 'quit',
            definition: '退出',
          }],
        })
      }
      if (url === '/api/books/word-details?word=quit') {
        return Promise.resolve({
          ...quietWordDetails,
          word: 'quit',
          definition: '退出',
        })
      }
      throw new Error(`Unexpected request: ${url}`)
    })

    renderLookup()
    const selectable = screen.getByTestId('selectable')
    mockSelection(selectable.firstChild as Text, 'quiet')
    fireEvent.pointerUp(selectable, { pointerType: 'mouse' })

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        '/api/books/search?q=quiet&limit=1',
        expect.objectContaining({ signal: expect.any(AbortSignal) }),
      )
    })

    mockSelection(selectable.firstChild as Text, 'quit')
    fireEvent.pointerUp(selectable, { pointerType: 'mouse' })

    await waitFor(() => {
      expect(firstSignal?.aborted).toBe(true)
    })

    await screen.findByRole('dialog', { name: '划词词典卡片：quit' })
    expect(document.querySelector('.selection-word-lookup-summary')).toHaveTextContent('adj. 退出')
  })

  it('closes the card on outside click, resize, and route change', async () => {
    apiFetchMock.mockImplementation((url: string) => {
      if (url === '/api/books/search?q=quiet&limit=1') {
        return Promise.resolve(quietSearchResult)
      }
      if (url === '/api/books/word-details?word=quiet') {
        return Promise.resolve(quietWordDetails)
      }
      throw new Error(`Unexpected request: ${url}`)
    })

    renderLookup()
    const selectable = screen.getByTestId('selectable')

    mockSelection(selectable.firstChild as Text, 'quiet')
    fireEvent.pointerUp(selectable, { pointerType: 'mouse' })
    await screen.findByRole('dialog', { name: '划词词典卡片：quiet' })

    fireEvent.pointerDown(document.body)
    await waitFor(() => {
      expect(screen.queryByRole('dialog', { name: '划词词典卡片：quiet' })).not.toBeInTheDocument()
    })

    mockSelection(selectable.firstChild as Text, 'quiet')
    fireEvent.pointerUp(selectable, { pointerType: 'mouse' })
    await screen.findByRole('dialog', { name: '划词词典卡片：quiet' })

    fireEvent(window, new Event('resize'))
    await waitFor(() => {
      expect(screen.queryByRole('dialog', { name: '划词词典卡片：quiet' })).not.toBeInTheDocument()
    })

    mockSelection(selectable.firstChild as Text, 'quiet')
    fireEvent.pointerUp(selectable, { pointerType: 'mouse' })
    await screen.findByRole('dialog', { name: '划词词典卡片：quiet' })

    await act(async () => {
      navigateRef?.('/books')
    })
    await waitFor(() => {
      expect(screen.queryByRole('dialog', { name: '划词词典卡片：quiet' })).not.toBeInTheDocument()
    })
  })

  it('opens the full detail view from the lightweight card', async () => {
    apiFetchMock.mockImplementation((url: string) => {
      if (url === '/api/books/search?q=quiet&limit=1') {
        return Promise.resolve(quietSearchResult)
      }
      if (url === '/api/books/word-details?word=quiet') {
        return Promise.resolve(quietWordDetails)
      }
      throw new Error(`Unexpected request: ${url}`)
    })

    renderLookup()
    const selectable = screen.getByTestId('selectable')
    mockSelection(selectable.firstChild as Text, 'quiet')
    fireEvent.pointerUp(selectable, { pointerType: 'mouse' })

    await screen.findByRole('dialog', { name: '划词词典卡片：quiet' })
    fireEvent.click(screen.getByRole('button', { name: '打开 quiet 的完整详情' }))

    expect(openGlobalWordSearchMock).toHaveBeenCalledWith({
      query: 'quiet',
      autoSubmit: true,
    })
  })
})
