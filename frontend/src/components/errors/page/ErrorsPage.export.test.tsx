import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { WrongWordRecord } from '../../../features/vocabulary/wrongWordsStore'
import ErrorsPage from './ErrorsPage'
import { buildWrongWordsCsvExportContent } from './errorsWordExport'

const navigateMock = vi.fn()

const hooksState = vi.hoisted(() => ({
  wrongWords: {
    loading: false,
    words: [
      {
        word: 'alpha',
        phonetic: '/a/',
        pos: 'n.',
        definition: '阿尔法',
        wrong_count: 6,
        first_wrong_at: '2026-04-07T02:00:00.000Z',
        meaning_wrong: 3,
      },
      {
        word: 'beta',
        phonetic: '/b/',
        pos: 'n.',
        definition: '贝塔',
        wrong_count: 5,
        first_wrong_at: '2026-04-07T04:00:00.000Z',
        meaning_wrong: 2,
      },
    ],
  },
}))

vi.mock('../../../features/vocabulary/hooks', () => ({
  useWrongWords: () => hooksState.wrongWords,
}))

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return {
    ...actual,
    useNavigate: () => navigateMock,
  }
})

describe('ErrorsPage export', () => {
  const createObjectURLMock = vi.fn(() => 'blob:wrong-words')
  const revokeObjectURLMock = vi.fn()
  let anchorClickSpy: ReturnType<typeof vi.spyOn>

  beforeEach(() => {
    createObjectURLMock.mockClear()
    revokeObjectURLMock.mockClear()
    navigateMock.mockReset()
    localStorage.clear()
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-04-10T08:00:00.000Z'))
    Object.defineProperty(globalThis.URL, 'createObjectURL', { value: createObjectURLMock, writable: true })
    Object.defineProperty(globalThis.URL, 'revokeObjectURL', { value: revokeObjectURLMock, writable: true })
    anchorClickSpy = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
  })

  afterEach(() => {
    vi.useRealTimers()
    anchorClickSpy.mockRestore()
  })

  it('builds csv content with only index, word, and chinese meaning columns', () => {
    expect(buildWrongWordsCsvExportContent(hooksState.wrongWords.words as WrongWordRecord[])).toBe(
      '序号,错词,中文意思\n1,alpha,阿尔法\n2,beta,贝塔',
    )
  })

  it('exports checked wrong words as a three-column csv download', () => {
    render(
      <MemoryRouter>
        <ErrorsPage />
      </MemoryRouter>,
    )

    const exportButton = screen.getByRole('button', { name: '导出已勾选 CSV' })
    expect(exportButton).toBeDisabled()

    fireEvent.click(screen.getByLabelText('选择 alpha'))
    expect(exportButton).not.toBeDisabled()

    fireEvent.click(exportButton)

    expect(createObjectURLMock).toHaveBeenCalledTimes(1)
    expect(revokeObjectURLMock).toHaveBeenCalledTimes(1)
    expect(anchorClickSpy).toHaveBeenCalledTimes(1)
  })
})
