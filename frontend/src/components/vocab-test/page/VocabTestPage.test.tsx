import React from 'react'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { act, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'
import VocabTestPage from './VocabTestPage'
import { playWordAudio } from '../../../features/practice/audio/practiceAudio'

vi.mock('../../../features/practice/audio/practiceAudio', async () => {
  const actual = await vi.importActual<typeof import('../../../features/practice/audio/practiceAudio')>('../../../features/practice/audio/practiceAudio')
  return {
    ...actual,
    playWordAudio: vi.fn(),
  }
})

describe('VocabTestPage', () => {
  const sampleWords = [
    { word: 'alpha', definition: '阿尔法', phonetic: '/a/', pos: 'n.' },
    { word: 'beta', definition: '贝塔', phonetic: '/b/', pos: 'n.' },
    { word: 'gamma', definition: '伽马', phonetic: '/g/', pos: 'n.' },
    { word: 'delta', definition: '德尔塔', phonetic: '/d/', pos: 'n.' },
    { word: 'epsilon', definition: '艾普西隆', phonetic: '/e/', pos: 'n.' },
  ]

  afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
  })

  async function flushQuestionLoad() {
    await act(async () => {
      await Promise.resolve()
      await Promise.resolve()
      await Promise.resolve()
    })
  }

  it('shows a page skeleton while vocabulary test words are loading', () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(
      () => new Promise(() => {}) as Promise<Response>,
    )

    const { container } = render(
      <MemoryRouter>
        <VocabTestPage />
      </MemoryRouter>,
    )

    expect(container.querySelector('.page-skeleton--quiz')).not.toBeNull()
    expect(container.querySelector('.loading-state')).toBeNull()
  })

  it('only auto-plays the first question once after load', async () => {
    vi.useFakeTimers()
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => ({ words: sampleWords }),
    } as Response)

    render(
      <MemoryRouter>
        <VocabTestPage />
      </MemoryRouter>,
    )

    await flushQuestionLoad()
    expect(screen.getByText('再听一遍')).toBeTruthy()

    act(() => {
      vi.advanceTimersByTime(1000)
    })

    expect(playWordAudio).toHaveBeenCalledTimes(1)
  })

  it('cancels pending auto-play when the user manually replays audio', async () => {
    vi.useFakeTimers()
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => ({ words: sampleWords }),
    } as Response)

    render(
      <MemoryRouter>
        <VocabTestPage />
      </MemoryRouter>,
    )

    await flushQuestionLoad()

    const replayButton = screen.getByText('再听一遍')
    fireEvent.click(replayButton)

    expect(playWordAudio).toHaveBeenCalledTimes(1)

    act(() => {
      vi.advanceTimersByTime(1000)
    })

    expect(playWordAudio).toHaveBeenCalledTimes(1)
  })

  it('keeps rendered quiz controls covered by the design-token stylesheet', () => {
    const stylesheet = readFileSync(
      resolve(__dirname, '../../../styles/pages/vocab-test/index.scss'),
      'utf8',
    )

    expect(stylesheet).toContain('.vocab-test-card')
    expect(stylesheet).toContain('.vocab-test-audio')
    expect(stylesheet).toContain('.vocab-test-option')
    expect(stylesheet).toContain('.vocab-test-option-index')
    expect(stylesheet).toContain('.vocab-test-secondary')
    expect(stylesheet).toContain('.vocab-test-primary')
  })

  it('centers the active quiz surface in the available page height', () => {
    const stylesheet = readFileSync(
      resolve(__dirname, '../../../styles/pages/vocab-test/index.scss'),
      'utf8',
    )

    expect(stylesheet).toMatch(/\.vocab-test\s*\{[^}]*justify-content:\s*center;/s)
  })
})
