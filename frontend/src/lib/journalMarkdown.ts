import { marked } from 'marked'
import DOMPurify from 'dompurify'

export function normalizeJournalMarkdown(markdown: string): string {
  const normalized = markdown
    .replace(/\r\n/g, '\n')
    .replace(/\s+---\s+/g, '\n\n---\n\n')
    .replace(/\s+(#{1,6}\s)/g, '\n\n$1')
    .replace(/\s+(>\s)/g, '\n\n$1')
    .replace(/\s+(-\s\*\*[^*\n]+?\*\*:)/g, '\n$1')
    .replace(/\s+(-\s)/g, '\n$1')
    .replace(/([^\n#])\s+(\d+\.\s)/g, '$1\n$2')
    .replace(/\|\s+(?=\|)/g, '|\n')
    .replace(/(#{1,6})\n(\d+\.\s)/g, '$1 $2')
    .replace(/\n{3,}/g, '\n\n')
    .trim()

  return normalized
    .split('\n')
    .flatMap((line) => {
      if (/^#{1,6}\s/.test(line) && line.includes(' | ')) {
        const splitIndex = line.indexOf(' | ')
        return [line.slice(0, splitIndex), `| ${line.slice(splitIndex + 3)}`]
      }
      return [line]
    })
    .join('\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim()
}

export function renderJournalMarkdown(markdown: string): string {
  const normalized = normalizeJournalMarkdown(markdown)
  const raw = marked.parse(normalized, {
    async: false,
    gfm: true,
    breaks: true,
  }) as string

  return DOMPurify.sanitize(raw, {
    ALLOWED_TAGS: ['h1', 'h2', 'h3', 'h4', 'p', 'strong', 'em', 'ul', 'ol', 'li', 'hr', 'br', 'code', 'pre', 'blockquote', 'table', 'thead', 'tbody', 'tr', 'th', 'td', 'a'],
    ALLOWED_ATTR: ['href', 'target', 'rel'],
  })
}
