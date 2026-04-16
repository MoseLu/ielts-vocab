import { useEffect, useMemo, useState } from 'react'

import type { ExamAttemptResultResponse, ExamPaperDetail, ExamQuestion, ExamSection } from '../../../lib'
import type { ExamResponseDraft } from '../../../features/exams/examApi'
import { sanitizeExamHtml } from '../../../features/exams/examHtml'
import { ExamQuestionFields } from './ExamQuestionFields'


interface ExamSectionWorkspaceProps {
  paper: ExamPaperDetail
  activeSection: ExamSection
  activeSectionId: number
  responseMap: Record<number, ExamResponseDraft>
  result: ExamAttemptResultResponse | null
  error: string
  isSubmitted: boolean
  onSelectSection: (sectionId: number, sectionType: string) => void
  onChangeResponse: (questionId: number, patch: Record<string, unknown>) => void
  onPersist: () => Promise<void>
}

interface WorkspaceBlock {
  key: string
  label: string
  meta: string
  documentHtml: string | null
  questions: ExamQuestion[]
  trackUrl: string | null
  trackTitle: string | null
}

interface QuestionGroup {
  key: string
  start: number
  end: number
  questions: ExamQuestion[]
}

function normalizeQuestionNumber(question: ExamQuestion): number {
  return question.questionNumber ?? question.sortOrder
}

function responseFilled(response: ExamResponseDraft | undefined) {
  const responseText = String(response?.responseText || '').trim()
  const selectedChoices = response?.selectedChoices || []
  const feedback = response?.feedback ? Object.keys(response.feedback) : []
  return Boolean(responseText || selectedChoices.length || feedback.length)
}

function countWords(value: string | undefined | null) {
  return String(value || '')
    .trim()
    .split(/\s+/)
    .filter(Boolean)
    .length
}

function parseGroupRange(groupKey: string, questions: ExamQuestion[]) {
  const match = groupKey.match(/(\d+)-(\d+)$/)
  if (match) {
    return { start: Number(match[1]), end: Number(match[2]) }
  }
  const numbers = questions.map(normalizeQuestionNumber)
  return {
    start: Math.min(...numbers),
    end: Math.max(...numbers),
  }
}

function buildQuestionGroups(section: ExamSection): QuestionGroup[] {
  const grouped = new Map<string, ExamQuestion[]>()
  section.questions.forEach(question => {
    const current = grouped.get(question.groupKey) || []
    current.push(question)
    grouped.set(question.groupKey, current)
  })

  return Array.from(grouped.entries())
    .map(([key, questions]) => {
      const range = parseGroupRange(key, questions)
      return {
        key,
        start: range.start,
        end: range.end,
        questions: [...questions].sort((left, right) => normalizeQuestionNumber(left) - normalizeQuestionNumber(right)),
      }
    })
    .sort((left, right) => left.start - right.start)
}

function findMarkerIndex(source: string, markers: string[], fromIndex = 0) {
  const lowerSource = source.toLowerCase()
  let candidate = -1
  markers.forEach(marker => {
    const index = lowerSource.indexOf(marker.toLowerCase(), fromIndex)
    if (index !== -1 && (candidate === -1 || index < candidate)) {
      candidate = index
    }
  })
  return candidate
}

function snapToParagraphStart(source: string, index: number) {
  const paragraphStart = source.lastIndexOf('<p', index)
  return paragraphStart === -1 ? index : paragraphStart
}

function extractHtmlSegment(source: string | null | undefined, startMarkers: string[], endMarkers: string[] = []) {
  if (!source) return null
  const markerIndex = findMarkerIndex(source, startMarkers)
  if (markerIndex === -1) return null
  const start = snapToParagraphStart(source, markerIndex)
  const nextMarkerIndex = endMarkers.length > 0
    ? findMarkerIndex(source, endMarkers, markerIndex + 1)
    : -1
  const end = nextMarkerIndex === -1 ? source.length : snapToParagraphStart(source, nextMarkerIndex)
  return source.slice(start, end).trim()
}

function splitOrderedGroups(groups: QuestionGroup[], blockCount: number) {
  if (groups.length === 0) return []
  if (blockCount <= 1 || groups.length <= 1) return [groups]

  const totalQuestions = groups.reduce((sum, group) => sum + group.questions.length, 0)
  const clusters: QuestionGroup[][] = []
  let assignedQuestions = 0
  let cursor = 0

  for (let blockIndex = 0; blockIndex < blockCount; blockIndex += 1) {
    const target = Math.round(totalQuestions * ((blockIndex + 1) / blockCount))
    const cluster: QuestionGroup[] = []

    while (cursor < groups.length) {
      const remainingBlocks = blockCount - blockIndex - 1
      const remainingGroups = groups.length - cursor
      const group = groups[cursor]
      cluster.push(group)
      cursor += 1
      assignedQuestions += group.questions.length
      if (assignedQuestions >= target && remainingGroups > remainingBlocks) break
      if (remainingGroups <= remainingBlocks) break
    }

    if (cluster.length > 0) {
      clusters.push(cluster)
    }
  }

  if (cursor < groups.length && clusters.length > 0) {
    clusters[clusters.length - 1] = [...clusters[clusters.length - 1], ...groups.slice(cursor)]
  }

  return clusters
}

function buildListeningBlocks(section: ExamSection): WorkspaceBlock[] {
  const ranges = [
    { label: 'Part 1', start: 1, end: 10 },
    { label: 'Part 2', start: 11, end: 20 },
    { label: 'Part 3', start: 21, end: 30 },
    { label: 'Part 4', start: 31, end: 40 },
  ]

  return ranges
    .map((range, index) => {
      const questions = section.questions.filter(question => {
        const number = normalizeQuestionNumber(question)
        return number >= range.start && number <= range.end
      })
      if (questions.length === 0) return null
      const track = section.audioTracks.find(item => item.partNumber === index + 1) || section.audioTracks[index]
      return {
        key: `listening-part-${index + 1}`,
        label: range.label,
        meta: `${range.start}-${range.end}`,
        documentHtml: extractHtmlSegment(
          section.htmlContent,
          [`section ${index + 1}`],
          index < ranges.length - 1 ? [`section ${index + 2}`] : [],
        ) || section.htmlContent || section.instructionsHtml || null,
        questions,
        trackUrl: track?.sourceUrl || null,
        trackTitle: track?.title || range.label,
      }
    })
    .filter((item): item is WorkspaceBlock => Boolean(item))
}

function buildReadingBlocks(section: ExamSection): WorkspaceBlock[] {
  const groups = buildQuestionGroups(section)
  const markerMatches = section.htmlContent?.match(/reading passage\s+\d/ig) || []
  const detectedBlockCount = section.passages.length > 0
    ? section.passages.length
    : Math.min(3, Math.max(markerMatches.length, groups.length > 0 ? 1 : 0))
  const clusters = splitOrderedGroups(groups, detectedBlockCount)

  return clusters.map((cluster, index) => {
    const questions = cluster.flatMap(group => group.questions)
    const first = questions[0]
    const last = questions[questions.length - 1]
    const passage = section.passages[index]
    return {
      key: `reading-passage-${index + 1}`,
      label: `Passage ${index + 1}`,
      meta: `${normalizeQuestionNumber(first)}-${normalizeQuestionNumber(last)}`,
      documentHtml: passage?.htmlContent || extractHtmlSegment(
        section.htmlContent,
        [`reading passage ${index + 1}`],
        index < clusters.length - 1 ? [`reading passage ${index + 2}`] : [],
      ) || section.htmlContent || null,
      questions,
      trackUrl: null,
      trackTitle: null,
    }
  })
}

function buildPromptBlocks(section: ExamSection, labelPrefix: string): WorkspaceBlock[] {
  return [...section.questions]
    .sort((left, right) => normalizeQuestionNumber(left) - normalizeQuestionNumber(right))
    .map((question, index) => ({
      key: `${section.sectionType}-${question.id}`,
      label: `${labelPrefix} ${index + 1}`,
      meta: `Q${normalizeQuestionNumber(question)}`,
      documentHtml: question.promptHtml,
      questions: [question],
      trackUrl: null,
      trackTitle: null,
    }))
}

function buildSectionBlocks(section: ExamSection): WorkspaceBlock[] {
  switch (section.sectionType) {
    case 'listening':
      return buildListeningBlocks(section)
    case 'reading':
      return buildReadingBlocks(section)
    case 'writing':
      return buildPromptBlocks(section, 'Task')
    case 'speaking':
      return buildPromptBlocks(section, 'Part')
    default:
      return [
        {
          key: `${section.sectionType}-${section.id}`,
          label: section.title,
          meta: `${section.questions.length} 题`,
          documentHtml: section.htmlContent || section.instructionsHtml || null,
          questions: section.questions,
          trackUrl: null,
          trackTitle: null,
        },
      ]
  }
}

function buildSectionTone(sectionType: string) {
  if (sectionType === 'listening') return 'is-listening'
  if (sectionType === 'reading') return 'is-reading'
  if (sectionType === 'writing') return 'is-writing'
  if (sectionType === 'speaking') return 'is-speaking'
  return ''
}

export function ExamSectionWorkspace({
  paper,
  activeSection,
  activeSectionId,
  responseMap,
  result,
  error,
  isSubmitted,
  onSelectSection,
  onChangeResponse,
  onPersist,
}: ExamSectionWorkspaceProps) {
  const blocks = useMemo(() => buildSectionBlocks(activeSection), [activeSection])
  const [activeBlockIndex, setActiveBlockIndex] = useState(0)

  useEffect(() => {
    setActiveBlockIndex(0)
  }, [activeSection.id])

  const activeBlock = blocks[activeBlockIndex] || blocks[0] || null
  const sectionTone = buildSectionTone(activeSection.sectionType)
  const answeredCount = activeSection.questions.filter(question => responseFilled(responseMap[question.id])).length
  const speakingOrWriting = activeSection.sectionType === 'writing' || activeSection.sectionType === 'speaking'
  const activePrompt = activeBlock?.questions[0] || null
  const activeWordCount = activePrompt ? countWords(responseMap[activePrompt.id]?.responseText) : 0

  if (!activeBlock) return null

  return (
    <div className={`exam-workspace ${sectionTone}`}>
      <div className="exam-workspace__topbar">
        <div className="exam-workspace__headline">
          <span className="exam-kicker">{paper.collectionTitle}</span>
          <div className="exam-workspace__title-row">
            <strong>{paper.title}</strong>
            <span>{activeSection.title}</span>
          </div>
        </div>

        <div className="exam-workspace__section-tabs" aria-label="Section switcher">
          {paper.sections.map(section => (
            <button
              key={section.id}
              type="button"
              className={`exam-section-tab ${section.id === activeSectionId ? 'is-active' : ''}`}
              onClick={() => onSelectSection(section.id, section.sectionType)}
            >
              <strong>{section.title}</strong>
              <span>{section.questions.length} 题</span>
            </button>
          ))}
        </div>

        <div className="exam-workspace__summary">
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
        </div>
      </div>

      <div className={`exam-workspace__canvas ${speakingOrWriting ? 'is-editor-layout' : ''}`}>
        <section className="exam-workspace-pane exam-workspace-pane--document">
          <div className="exam-workspace-pane__header">
            <div>
              <strong>{activeBlock.label}</strong>
              <span>{activeBlock.meta}</span>
            </div>
            {activeSection.instructionsHtml && activeSection.sectionType !== 'speaking' && (
              <span className="exam-workspace-pane__hint">请按题面要求作答</span>
            )}
          </div>

          {activeSection.instructionsHtml && (
            <div
              className="exam-workspace-pane__intro"
              dangerouslySetInnerHTML={{ __html: sanitizeExamHtml(activeSection.instructionsHtml) }}
            />
          )}

          {activeBlock.trackUrl && (
            <div className="exam-audio-panel">
              <div className="exam-audio-panel__meta">
                <strong>{activeBlock.trackTitle || activeBlock.label}</strong>
                <span>音频已就绪</span>
              </div>
              <audio controls src={activeBlock.trackUrl} />
            </div>
          )}

          <div className="exam-workspace-pane__scroll">
            {activeBlock.documentHtml ? (
              <article
                className="exam-document"
                dangerouslySetInnerHTML={{ __html: sanitizeExamHtml(activeBlock.documentHtml) }}
              />
            ) : (
              <div className="exam-document exam-document--empty">当前题组暂无可展示材料。</div>
            )}
          </div>
        </section>

        <section className="exam-workspace-pane exam-workspace-pane--answers">
          <div className="exam-workspace-pane__header">
            <div>
              <strong>{speakingOrWriting ? '作答区' : '答题区'}</strong>
              <span>
                {speakingOrWriting
                  ? activePrompt
                    ? `Q${normalizeQuestionNumber(activePrompt)}`
                    : activeBlock.meta
                  : `${activeBlock.questions.length} 题`}
              </span>
            </div>
            {activeSection.sectionType === 'writing' && (
              <span className="exam-workspace-pane__hint">Word count: {activeWordCount}</span>
            )}
          </div>

          {error && <div className="exam-inline-error exam-inline-error--banner">{error}</div>}

          <div className="exam-workspace-pane__scroll">
            {speakingOrWriting && activePrompt ? (
              <div className="exam-editor-shell">
                <div
                  className="exam-editor-shell__prompt"
                  dangerouslySetInnerHTML={{ __html: sanitizeExamHtml(activePrompt.promptHtml) }}
                />
                <div className="exam-editor-shell__field">
                  <ExamQuestionFields
                    question={activePrompt}
                    response={responseMap[activePrompt.id] || null}
                    disabled={isSubmitted}
                    hidePrompt
                    className="exam-question-fields--editor"
                    onChange={onChangeResponse}
                    onPersist={onPersist}
                  />
                </div>
              </div>
            ) : (
              <div className="exam-question-stack">
                {activeBlock.questions.map(question => (
                  <article key={question.id} id={`exam-question-${question.id}`} className="exam-question-card">
                    <div className="exam-question-card__meta">
                      <span>Q{normalizeQuestionNumber(question)}</span>
                      <span>{question.questionType}</span>
                    </div>
                    <ExamQuestionFields
                      question={question}
                      response={responseMap[question.id] || null}
                      disabled={isSubmitted}
                      onChange={onChangeResponse}
                      onPersist={onPersist}
                    />
                  </article>
                ))}
              </div>
            )}
          </div>
        </section>
      </div>

      <div className="exam-workspace__footer">
        <div className="exam-block-tabs" aria-label="Block navigator">
          {blocks.map((block, index) => (
            <button
              key={block.key}
              type="button"
              className={`exam-block-tab ${index === activeBlockIndex ? 'is-active' : ''}`}
              onClick={() => setActiveBlockIndex(index)}
            >
              <strong>{block.label}</strong>
              <span>{block.meta}</span>
            </button>
          ))}
        </div>

        {!speakingOrWriting && (
          <div className="exam-question-jump" aria-label="Question navigator">
            {activeBlock.questions.map(question => {
              const answered = responseFilled(responseMap[question.id])
              return (
                <a
                  key={question.id}
                  className={`exam-question-chip ${answered ? 'is-answered' : ''}`}
                  href={`#exam-question-${question.id}`}
                >
                  {normalizeQuestionNumber(question)}
                </a>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}

export default ExamSectionWorkspace
