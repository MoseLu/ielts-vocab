import DOMPurify from 'dompurify'

const EXAM_ALLOWED_TAGS = [
  'article', 'aside', 'b', 'blockquote', 'br', 'caption', 'code', 'div',
  'em', 'figcaption', 'figure', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'hr',
  'i', 'img', 'li', 'ol', 'p', 'pre', 'section', 'small', 'span', 'strong',
  'sub', 'sup', 'table', 'tbody', 'td', 'tfoot', 'th', 'thead', 'tr', 'u', 'ul',
]

const EXAM_ALLOWED_ATTR = ['alt', 'class', 'colspan', 'rowspan', 'scope', 'src', 'title']

const OCR_MARKUP_REPLACEMENTS: Array<[RegExp, string]> = [
  [/<p>\s*Testi\s*<br\s*\/?>/gi, '<p>'],
  [/<p>\s*READING\s*<br\s*\/?>\s*(?=READING PASSAGE)/g, '<p>'],
  [/<p>\s*(?:Reading|Listening)\s*(?=<br\s*\/?>\s*Questions\s+\d)/gi, '<p>'],
  [/<br\s*\/?>\s*(?:Reading|Listening)\s*(?=<br\s*\/?>\s*Questions\s+\d)/gi, ''],
  [/<br\s*\/?>\s*[®◎•]\s*(?=<br\s*\/?>)/g, ''],
  [/<br\s*\/?>\s*(?:[1-9]|[1-3][0-9]|40)\s*<\/p>/g, '</p>'],
]

const OCR_TEXT_REPLACEMENTS: Array<[RegExp, string]> = [
  [/\bACADEMBC\b/gi, 'ACADEMIC'],
  [/\bassessi ng\b/gi, 'assessing'],
  [/\bIan guage\b/gi, 'language'],
  [/\bIanguage\b/gi, 'language'],
  [/\bcan didates\b/gi, 'candidates'],
  [/\bcan didate\b/gi, 'candidate'],
  [/\bn eed\b/gi, 'need'],
  [/\bdesig ned\b/gi, 'designed'],
  [/\bEn glish\b/gi, 'English'],
  [/\bcon sists\b/gi, 'consists'],
  [/\bcomp orients\b/gi, 'components'],
  [/\bListe ning\b/gi, 'Listening'],
  [/\bReadi ng\b/gi, 'Reading'],
  [/\bsecti on\b/gi, 'section'],
  [/\bconversati on\b/gi, 'conversation'],
  [/\btraini ng\b/gi, 'training'],
  [/\bcon texts\b/gi, 'contexts'],
  [/\bmformation\b/gi, 'information'],
  [/\bPersonal mformation\b/gi, 'Personal information'],
  [/\bNatio nality\b/g, 'Nationality'],
  [/\bOccupati on\b/g, 'Occupation'],
  [/\bin terior\b/g, 'interior'],
  [/\bdesig ner\b/g, 'designer'],
  [/\bReas on\b/g, 'Reason'],
  [/\bCsime\b/g, 'Crime'],
  [/\baSiocated\b/g, 'allocated'],
  [/\bldngdom\b/gi, 'kingdom'],
  [/\bWlien\b/g, 'When'],
  [/\bin creased\b/gi, 'increased'],
  [/\bbetter9\b/g, 'better'],
  [/\bchildren\^\s+play\b/gi, "children's play"],
  [/\ba 'magical kingdom\b/gi, 'a magical kingdom'],
]

export function normalizeExamMarkup(content: string | null | undefined): string {
  let normalized = String(content || '').replace(/\r\n?/g, '\n')

  OCR_MARKUP_REPLACEMENTS.forEach(([pattern, replacement]) => {
    normalized = normalized.replace(pattern, replacement)
  })

  OCR_TEXT_REPLACEMENTS.forEach(([pattern, replacement]) => {
    normalized = normalized.replace(pattern, replacement)
  })

  normalized = normalized
    .replace(/([A-Za-z])，([A-Za-z])/g, "$1'$2")
    .replace(/([A-Za-z])[‘’]([A-Za-z])/g, "$1'$2")
    .replace(/([A-Za-z])\^([A-Za-z])/g, "$1'$2")
    .replace(/\b([A-Za-z]{4,})5\b/g, "$1'")
    .replace(/([A-Za-z])[\u3400-\u9FFF]+(?=[.]{3,}|<br|<\/p>|\s)/g, '$1')
    .replace(/[®◎]/g, '•')
    .replace(/一\s+/g, '- ')
    .replace(/\b([A-Za-z]{2,}[.!?])\s+[1-9]\s+([A-Z])/g, '$1 $2')
    .replace(/\s+([,.;:!?])/g, '$1')
    .replace(/\(\s+/g, '(')
    .replace(/\s+\)/g, ')')
    .replace(/>\s+</g, '><')

  return normalized
}

export function sanitizeExamHtml(content: string | null | undefined): string {
  return DOMPurify.sanitize(normalizeExamMarkup(content), {
    ALLOWED_TAGS: EXAM_ALLOWED_TAGS,
    ALLOWED_ATTR: EXAM_ALLOWED_ATTR,
  })
}
