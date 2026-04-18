import { useNavigate, useParams, useSearchParams } from 'react-router-dom'

import { Page, PageContent, PageHeader } from '../../layout'
import { EmptyState, PageSkeleton } from '../../ui'
import { useExamAttemptPage } from '../../../composables/exams/page/useExamAttemptPage'
import { ExamSectionWorkspace } from './ExamSectionWorkspace'


function formatElapsed(seconds: number): string {
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const remainSeconds = seconds % 60
  if (hours > 0) return `${hours}:${String(minutes).padStart(2, '0')}:${String(remainSeconds).padStart(2, '0')}`
  return `${String(minutes).padStart(2, '0')}:${String(remainSeconds).padStart(2, '0')}`
}

function responseFilled(response: { responseText?: string | null; selectedChoices?: string[]; feedback?: Record<string, unknown> } | undefined) {
  const responseText = String(response?.responseText || '').trim()
  const selectedChoices = response?.selectedChoices || []
  const feedback = response?.feedback ? Object.keys(response.feedback) : []
  return Boolean(responseText || selectedChoices.length || feedback.length)
}

export default function ExamAttemptPage() {
  const navigate = useNavigate()
  const { paperId: paperIdParam } = useParams()
  const [searchParams, setSearchParams] = useSearchParams()
  const paperId = Number(paperIdParam)
  const requestedSectionType = searchParams.get('section')

  const {
    paper,
    attempt,
    result,
    responseMap,
    activeSection,
    activeSectionId,
    elapsedSeconds,
    loading,
    saving,
    submitting,
    error,
    setActiveSectionId,
    updateResponse,
    flushResponses,
    submit,
  } = useExamAttemptPage(paperId, requestedSectionType)

  if (!Number.isFinite(paperId) || paperId <= 0) {
    return (
      <Page className="exam-attempt-page">
        <PageContent>
          <EmptyState page title="试卷不存在" description="无效的试卷编号。" />
        </PageContent>
      </Page>
    )
  }

  if (loading) {
    return (
      <Page className="exam-attempt-page">
        <PageContent>
          <PageSkeleton variant="quiz" />
        </PageContent>
      </Page>
    )
  }

  if (!paper || !activeSection) {
    return (
      <Page className="exam-attempt-page">
        <PageContent>
          <EmptyState page title="试卷加载失败" description={error || '当前试卷暂不可用。'} />
        </PageContent>
      </Page>
    )
  }

  const isSubmitted = attempt?.status === 'submitted'
  const answeredCount = activeSection.questions.filter(question => responseFilled(responseMap[question.id])).length

  return (
    <Page className="exam-attempt-page">
      <PageHeader className="exam-attempt-page__header">
        <div className="exam-attempt-page__toolbar">
          <div className="exam-attempt-page__lead">
            <button type="button" className="exam-action-button" onClick={() => navigate('/exams')}>
              返回题库
            </button>

            <div className="exam-attempt-page__identity">
              <span className="exam-kicker">{paper.collectionTitle}</span>
              <strong>{paper.title}</strong>
              <span className="exam-attempt-page__section-label">{activeSection.title}</span>
            </div>
          </div>

          <div className="exam-attempt-page__section-tabs" aria-label="Section switcher">
            {paper.sections.map(section => (
              <button
                key={section.id}
                type="button"
                className={`exam-section-tab ${section.id === activeSectionId ? 'is-active' : ''}`}
                onClick={() => {
                  setActiveSectionId(section.id)
                  setSearchParams({ section: section.sectionType })
                }}
              >
                <strong>{section.title}</strong>
                <span>{section.questions.length} 题</span>
              </button>
            ))}
          </div>

          <div className="exam-attempt-page__meta">
            <span>已用 {formatElapsed(elapsedSeconds)}</span>
            <span>{saving ? '保存中' : '自动保存'}</span>
            <div className="exam-summary-pill">
              <span>进度</span>
              <strong>{answeredCount}/{activeSection.questions.length}</strong>
            </div>
            {result && (
              <div className="exam-summary-pill">
                <span>得分</span>
                <strong>{result.summary.objectiveCorrect}/{result.summary.objectiveTotal}</strong>
              </div>
            )}
            <button
              type="button"
              className="exam-action-button exam-action-button--accent"
              disabled={submitting || isSubmitted}
              onClick={() => void submit()}
            >
              {isSubmitted ? '已提交' : submitting ? '提交中...' : '提交试卷'}
            </button>
          </div>
        </div>
      </PageHeader>

      <PageContent className="exam-attempt-page__body">
        <ExamSectionWorkspace
          activeSection={activeSection}
          responseMap={responseMap}
          error={error}
          isSubmitted={isSubmitted}
          onChangeResponse={updateResponse}
          onPersist={() => flushResponses(true)}
        />
      </PageContent>
    </Page>
  )
}
