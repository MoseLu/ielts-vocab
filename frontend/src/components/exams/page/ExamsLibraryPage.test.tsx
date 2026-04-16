import React from 'react'
import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'

import ExamsLibraryPage from './ExamsLibraryPage'


const navigateMock = vi.fn()

function createCollections() {
  return [
    {
      key: 'IELTS Academic 20',
      title: 'IELTS Academic 20',
      papers: [
        {
          id: 1,
          collectionTitle: 'IELTS Academic 20',
          title: 'Test 1',
          seriesNumber: 20,
          testNumber: 1,
          examKind: 'academic',
          publishStatus: 'published_internal',
          rightsStatus: 'internal',
          importConfidence: 0.99,
          answerKeyConfidence: 0.97,
          hasListeningAudio: true,
          reviewCount: 0,
          sections: [
            {
              id: 11,
              sectionType: 'listening',
              title: 'Listening Section',
              audioTracks: [{ title: 'Part 1' }],
              questionCount: 40,
            },
            {
              id: 12,
              sectionType: 'reading',
              title: 'Reading Section',
              audioTracks: [],
              questionCount: 40,
            },
          ],
          latestAttempt: null,
        },
      ],
    },
    {
      key: 'IELTS Academic 19',
      title: 'IELTS Academic 19',
      papers: [
        {
          id: 2,
          collectionTitle: 'IELTS Academic 19',
          title: 'Test 2',
          seriesNumber: 19,
          testNumber: 2,
          examKind: 'academic',
          publishStatus: 'published_internal',
          rightsStatus: 'internal',
          importConfidence: 0.99,
          answerKeyConfidence: 0.95,
          hasListeningAudio: true,
          reviewCount: 0,
          sections: [
            {
              id: 21,
              sectionType: 'writing',
              title: 'Writing Task 1',
              audioTracks: [],
              questionCount: 2,
            },
            {
              id: 22,
              sectionType: 'speaking',
              title: 'Speaking Prompt',
              audioTracks: [],
              questionCount: 3,
            },
          ],
          latestAttempt: {
            id: 8,
            paperId: 2,
            status: 'in_progress',
            objectiveCorrect: 0,
            objectiveTotal: 0,
            autoScore: 0,
            maxScore: 0,
            feedback: {},
            startedAt: null,
            submittedAt: null,
            responses: [],
          },
        },
      ],
    },
  ]
}

const hookState = vi.hoisted(() => ({
  collections: createCollections(),
  loading: false,
  error: '',
}))

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return {
    ...actual,
    useNavigate: () => navigateMock,
  }
})

vi.mock('../../../composables/exams/page/useExamsLibraryPage', () => ({
  useExamsLibraryPage: () => hookState,
}))

describe('ExamsLibraryPage', () => {
  beforeEach(() => {
    navigateMock.mockReset()
    hookState.collections = createCollections()
    hookState.loading = false
    hookState.error = ''
  })

  it('reuses the compact wordbook filter rows', () => {
    const { container } = render(
      <MemoryRouter>
        <ExamsLibraryPage />
      </MemoryRouter>,
    )

    const filterRows = container.querySelectorAll('.vb-filter-row')
    const filterButtons = container.querySelectorAll('.vb-filter-btn')

    expect(filterRows).toHaveLength(3)
    filterRows.forEach(row => {
      expect(row).toHaveClass('vb-filter-row--compact')
    })
    filterButtons.forEach(button => {
      expect(button).toHaveClass('vb-filter-btn--compact')
    })

    expect(screen.getAllByText('剑雅20').length).toBeGreaterThan(0)
    expect(screen.getAllByText('剑雅19').length).toBeGreaterThan(0)
  })

  it('filters cards by selected section mode', () => {
    render(
      <MemoryRouter>
        <ExamsLibraryPage />
      </MemoryRouter>,
    )

    fireEvent.click(screen.getByRole('button', { name: '写作' }))

    expect(screen.getByText('Writing Task 1')).toBeInTheDocument()
    expect(screen.queryByText('Listening Section')).toBeNull()
    expect(screen.queryByText('Reading Section')).toBeNull()
  })

  it('navigates to the selected section when a module button is clicked', () => {
    render(
      <MemoryRouter>
        <ExamsLibraryPage />
      </MemoryRouter>,
    )

    const readingButton = screen.getByText('Reading Section').closest('button')
    expect(readingButton).not.toBeNull()

    fireEvent.click(readingButton!)

    expect(navigateMock).toHaveBeenCalledWith('/exams/1?section=reading')
  })
})
