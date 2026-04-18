import { sanitizeExamHtml } from '../../../features/exams/examHtml'

interface ExamDocumentContentProps {
  html: string
  sectionType: string
}

const READING_INTRO_PATTERN = /^You should spend about|^Questions \d+/i
const SPEAKER_PATTERN = /^([A-Za-z][A-Za-z ]+)\s*[:：]\s*(.*)$/

function buildPlainLines(html: string) {
  return sanitizeExamHtml(html)
    .replace(/<\/p>/gi, '\n\n')
    .replace(/<br\s*\/?>/gi, '\n')
    .replace(/<[^>]+>/g, '')
    .split('\n')
    .map(line => line.replace(/\s+/g, ' ').trim())
    .filter(Boolean)
}

function looksLikeReadingTitle(line: string, nextLine: string) {
  if (!line || !nextLine) return false
  if (READING_INTRO_PATTERN.test(line) || /^READING PASSAGE \d+$/i.test(line) || line === 'Introduction') return false
  const wordCount = line.split(/\s+/).filter(Boolean).length
  const shortHeading = wordCount <= 10 && line.length <= 80
  const hasSentenceEnding = /[.!?]$/.test(line)
  const nextLooksLikeProse = nextLine.length >= 60 || /[.!?]["']?$/.test(nextLine)
  return shortHeading && !hasSentenceEnding && nextLooksLikeProse
}

function renderReadingDocument(lines: string[]) {
  const cleaned = lines.filter(line => !/^Testi$/i.test(line) && line !== 'Introduction')
  const heading = cleaned.find(line => /^READING PASSAGE \d+$/i.test(line)) || ''
  const intro = cleaned.filter(line => READING_INTRO_PATTERN.test(line))
  const titleIndex = cleaned.findIndex((line, index) => {
    if (/^[A-Z' ]{8,}$/.test(line) && !/^READING PASSAGE \d+$/i.test(line)) return true
    return looksLikeReadingTitle(line, cleaned[index + 1] || '')
  })
  const title = titleIndex >= 0 ? cleaned[titleIndex] : ''
  const proseLines = cleaned.slice(titleIndex >= 0 ? titleIndex + 1 : 0)
  const paragraphs: string[] = []
  let buffer = ''

  proseLines.forEach(line => {
    if (READING_INTRO_PATTERN.test(line)) return
    buffer = buffer ? `${buffer} ${line}` : line
    if (buffer.length >= 260 || /[.!?]["']?$/.test(line)) {
      paragraphs.push(buffer)
      buffer = ''
    }
  })

  if (buffer) {
    paragraphs.push(buffer)
  }

  return (
    <div className="exam-reading-doc">
      {heading && <p className="exam-reading-doc__eyebrow">{heading}</p>}
      {intro.length > 0 && (
        <div className="exam-reading-doc__intro">
          {intro.map(line => <p key={line}>{line}</p>)}
        </div>
      )}
      {title && <h3 className="exam-reading-doc__title">{title}</h3>}
      <div className="exam-reading-doc__body">
        {paragraphs.map((paragraph, index) => (
          <p key={`${index}-${paragraph.slice(0, 18)}`} className="exam-reading-doc__paragraph">
            {paragraph}
          </p>
        ))}
      </div>
    </div>
  )
}

function renderTranscriptDocument(lines: string[]) {
  const blocks: Array<{ speaker: string; body: string[] }> = []

  lines.forEach(line => {
    const speakerMatch = line.match(SPEAKER_PATTERN)
    if (speakerMatch) {
      blocks.push({ speaker: speakerMatch[1].toUpperCase(), body: [speakerMatch[2]].filter(Boolean) })
      return
    }

    if (blocks.length === 0) {
      blocks.push({ speaker: '', body: [line] })
      return
    }

    blocks[blocks.length - 1].body.push(line)
  })

  return (
    <div className="exam-transcript">
      {blocks.map((block, index) => (
        <article key={`${block.speaker}-${index}`} className="exam-transcript__block">
          {block.speaker && <h4 className="exam-transcript__speaker">{block.speaker}:</h4>}
          {block.body.map((line, bodyIndex) => (
            <p
              key={`${index}-${bodyIndex}`}
              className={/[\u3400-\u9FFF]/.test(line) ? 'exam-transcript__translation' : 'exam-transcript__line'}
            >
              {line}
            </p>
          ))}
        </article>
      ))}
    </div>
  )
}

export function ExamDocumentContent({ html, sectionType }: ExamDocumentContentProps) {
  const lines = buildPlainLines(html)

  if (sectionType === 'reading' && lines.length > 0) {
    return renderReadingDocument(lines)
  }

  if (sectionType === 'listening' && lines.some(line => SPEAKER_PATTERN.test(line))) {
    return renderTranscriptDocument(lines)
  }

  return (
    <article
      className="exam-document"
      dangerouslySetInnerHTML={{ __html: sanitizeExamHtml(html) }}
    />
  )
}

export default ExamDocumentContent
