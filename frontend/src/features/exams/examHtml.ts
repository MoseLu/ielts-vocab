import DOMPurify from 'dompurify'


const EXAM_ALLOWED_TAGS = [
  'article',
  'aside',
  'b',
  'blockquote',
  'br',
  'caption',
  'code',
  'div',
  'em',
  'figcaption',
  'figure',
  'h1',
  'h2',
  'h3',
  'h4',
  'h5',
  'h6',
  'hr',
  'i',
  'img',
  'li',
  'ol',
  'p',
  'pre',
  'section',
  'small',
  'span',
  'strong',
  'sub',
  'sup',
  'table',
  'tbody',
  'td',
  'tfoot',
  'th',
  'thead',
  'tr',
  'u',
  'ul',
]

const EXAM_ALLOWED_ATTR = [
  'alt',
  'class',
  'colspan',
  'rowspan',
  'scope',
  'src',
  'title',
]

export function sanitizeExamHtml(content: string | null | undefined): string {
  return DOMPurify.sanitize(content || '', {
    ALLOWED_TAGS: EXAM_ALLOWED_TAGS,
    ALLOWED_ATTR: EXAM_ALLOWED_ATTR,
  })
}
