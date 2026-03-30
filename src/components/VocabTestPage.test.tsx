import React from 'react'
import { render } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'
import VocabTestPage from './VocabTestPage'

vi.mock('./practice/utils', async () => {
  const actual = await vi.importActual<typeof import('./practice/utils')>('./practice/utils')
  return {
    ...actual,
    playWordAudio: vi.fn(),
  }
})

describe('VocabTestPage', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

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
})
