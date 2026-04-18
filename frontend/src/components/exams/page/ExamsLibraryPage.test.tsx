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
              questionCount: 1,
            },
            {
              id: 12,
              sectionType: 'reading',
              title: 'Reading Section',
              audioTracks: [],
              questionCount: 1,
            },
            {
              id: 13,
              sectionType: 'writing',
              title: 'Writing Section',
              audioTracks: [],
              questionCount: 1,
            },
          ],
          latestAttempt: {
            id: 7,
            paperId: 1,
            status: 'submitted',
            objectiveCorrect: 0,
            objectiveTotal: 1,
            autoScore: 0,
            maxScore: 1,
            feedback: {},
            startedAt: null,
            submittedAt: null,
            responses: [
              {
                id: 701,
                questionId: 1101,
                responseText: 'hotel',
                selectedChoices: [],
                attachmentUrl: null,
                durationSeconds: null,
                isCorrect: false,
                score: 0,
                feedback: {},
              },
            ],
          },
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
  questionIndexMap: {
    1: {
      paperQuestionFilters: ['fill_blank', 'single_choice', 'judgement'],
      sectionQuestionFilters: {
        11: ['fill_blank'],
        12: ['single_choice', 'judgement'],
        13: [],
      },
      sectionQuestionIds: {
        11: [1101],
        12: [1201],
        13: [1301],
      },
    },
    2: {
      paperQuestionFilters: [],
      sectionQuestionFilters: {
        21: [],
        22: [],
      },
      sectionQuestionIds: {
        21: [2101],
        22: [2201],
      },
    },
  },
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
    hookState.questionIndexMap = {
      1: {
        paperQuestionFilters: ['fill_blank', 'single_choice', 'judgement'],
        sectionQuestionFilters: {
          11: ['fill_blank'],
          12: ['single_choice', 'judgement'],
          13: [],
        },
        sectionQuestionIds: {
          11: [1101],
          12: [1201],
          13: [1301],
        },
      },
      2: {
        paperQuestionFilters: [],
        sectionQuestionFilters: {
          21: [],
          22: [],
        },
        sectionQuestionIds: {
          21: [2101],
          22: [2201],
        },
      },
    }
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

    expect(screen.getByRole('button', { name: '填空题' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '单选题' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '多选题' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '匹配题' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '判断题' })).toBeInTheDocument()
  })

  it('filters cards by selected section mode', () => {
    render(
      <MemoryRouter>
        <ExamsLibraryPage />
      </MemoryRouter>,
    )

    fireEvent.click(screen.getByRole('button', { name: '写作' }))

    expect(screen.getAllByRole('button', { name: 'Writing' }).length).toBeGreaterThan(0)
    expect(screen.queryByRole('button', { name: 'Listening' })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Reading' })).toBeNull()
  })

  it('filters cards by selected question type', () => {
    render(
      <MemoryRouter>
        <ExamsLibraryPage />
      </MemoryRouter>,
    )

    fireEvent.click(screen.getByRole('button', { name: '判断题' }))

    expect(screen.getByRole('button', { name: 'Reading' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Listening' })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Writing' })).toBeNull()
  })

  it('renders row-level metrics and excludes speaking rows from test cards', () => {
    const { container } = render(
      <MemoryRouter>
        <ExamsLibraryPage />
      </MemoryRouter>,
    )

    expect(screen.queryByRole('button', { name: 'Speaking' })).toBeNull()
    expect(screen.getByText('0分')).toBeInTheDocument()
    expect(container.querySelector('.exam-series-paper__check')).not.toBeNull()
  })

  it('navigates to the selected section when a module button is clicked', () => {
    render(
      <MemoryRouter>
        <ExamsLibraryPage />
      </MemoryRouter>,
    )

    fireEvent.click(screen.getByRole('button', { name: 'Reading' }))

    expect(navigateMock).toHaveBeenCalledWith('/exams/1?section=reading')
  })
})
