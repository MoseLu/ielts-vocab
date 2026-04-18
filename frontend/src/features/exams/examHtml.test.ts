import { describe, expect, it } from 'vitest'

import { normalizeExamMarkup, sanitizeExamHtml } from './examHtml'

describe('examHtml', () => {
  it('removes page chrome noise around question blocks', () => {
    const source = '<p>Testi<br/>Reading<br/>Questions 1-8<br/>Prompt line<br/>8</p>'
    const normalized = normalizeExamMarkup(source)

    expect(normalized).not.toContain('Testi')
    expect(normalized).not.toContain('>Reading<br/>Questions')
    expect(normalized).not.toContain('<br/>8</p>')
    expect(normalized).toContain('Questions 1-8')
  })

  it('fixes common OCR-broken words', () => {
    const source = '<p>Personal mformation<br/>Natio nality<br/>Occupati on<br/>in terior desig ner</p>'
    const normalized = normalizeExamMarkup(source)

    expect(normalized).toContain('Personal information')
    expect(normalized).toContain('Nationality')
    expect(normalized).toContain('Occupation')
    expect(normalized).toContain('interior designer')
  })

  it('sanitizes after normalization', () => {
    const sanitized = sanitizeExamHtml('<p>Louise感饥.......</p><script>alert(1)</script>')

    expect(sanitized).toContain('Louise.......')
    expect(sanitized).not.toContain('<script>')
  })
})
