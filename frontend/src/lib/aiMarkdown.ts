import DOMPurify from 'dompurify'
import { marked } from 'marked'

const SANITIZE_OPTIONS = {
  ALLOWED_TAGS: [
    'h1',
    'h2',
    'h3',
    'h4',
    'p',
    'strong',
    'em',
    'ul',
    'ol',
    'li',
    'hr',
    'br',
    'code',
    'pre',
    'blockquote',
    'table',
    'thead',
    'tbody',
    'tr',
    'th',
    'td',
    'a',
  ],
  ALLOWED_ATTR: ['href', 'target', 'rel'],
}

function unwrapMarkdownFence(markdown: string): string {
  const match = markdown.trim().match(/^```(?:markdown|md)\s*\n([\s\S]*?)\n```$/i)
  return match?.[1]?.trim() ?? markdown
}

function normalizeOutsideCodeBlocks(markdown: string, normalize: (chunk: string) => string): string {
  const parts = markdown.split(/(```[\s\S]*?```)/g)
  return parts.map((part) => (part.startsWith('```') ? part : normalize(part))).join('')
}

function separateTableBlocks(markdown: string): string {
  const lines = markdown.split('\n')
  const separated: string[] = []
  let previousWasTable = false

  lines.forEach((line) => {
    const isTableLine = /^\s*\|.*\|\s*$/.test(line)
    const previous = separated[separated.length - 1]

    if (isTableLine && !previousWasTable && previous?.trim()) {
      separated.push('')
    }
    if (!isTableLine && previousWasTable && line.trim()) {
      separated.push('')
    }

    separated.push(line)
    previousWasTable = isTableLine
  })

  return separated.join('\n')
}

function splitInlineTableRows(markdown: string): string {
  return markdown
    .split('\n')
    .flatMap((line) => {
      const firstPipe = line.indexOf('|')
      const lastPipe = line.lastIndexOf('|')

      if (firstPipe < 0 || lastPipe <= firstPipe) {
        return [line]
      }

      return [
        line.slice(0, firstPipe).trimEnd(),
        line.slice(firstPipe, lastPipe + 1).trim(),
        line.slice(lastPipe + 1).trimStart(),
      ].filter(Boolean)
    })
    .join('\n')
}

function normalizeMarkdownChunk(chunk: string): string {
  const normalized = chunk
    .replace(/\r\n/g, '\n')
    .replace(/\s+---\s+/g, '\n\n---\n\n')
    .replace(/([^\n])(\n?#{1,4}\s)/g, '$1\n\n$2')
    .replace(/([^\n])(\n?>\s)/g, '$1\n\n$2')
    .replace(/([^\n])(\n?[-*]\s+)/g, '$1\n$2')
    .replace(/([^\n])(\n?\d+\.\s+)/g, '$1\n$2')
    .replace(/\|\s+(?=\|)/g, '|\n')
    .replace(/\n{3,}/g, '\n\n')

  return separateTableBlocks(splitInlineTableRows(normalized))
}

export function normalizeAIResponseMarkdown(markdown: string): string {
  return normalizeOutsideCodeBlocks(unwrapMarkdownFence(markdown), normalizeMarkdownChunk)
    .replace(/\n{3,}/g, '\n\n')
    .trim()
}

export function renderAIResponseMarkdown(markdown: string): string {
  const raw = marked.parse(normalizeAIResponseMarkdown(markdown), {
    async: false,
    breaks: true,
    gfm: true,
  }) as string

  return DOMPurify.sanitize(raw, SANITIZE_OPTIONS)
}
