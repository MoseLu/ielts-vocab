import { describe, expect, it } from 'vitest'
import { normalizeJournalMarkdown, renderJournalMarkdown } from './journalMarkdown'

describe('journalMarkdown', () => {
  it('restores line breaks for compressed markdown summaries', () => {
    const compressed = '# Title --- ## 1. Overview | 项目 | 数据 | |------|------| | 学习模式 | 随身听模式 | > 提示 - 第一条 1. 下一步'
    const normalized = normalizeJournalMarkdown(compressed)

    expect(normalized).toContain('# Title\n\n---\n\n## 1. Overview')
    expect(normalized).toContain('| 项目 | 数据 |\n|------|------|')
    expect(normalized).toContain('\n> 提示')
    expect(normalized).toContain('\n- 第一条')
    expect(normalized).toContain('\n1. 下一步')
  })

  it('renders headings, tables and lists into html', () => {
    const html = renderJournalMarkdown('# Title --- ## 1. Overview | 项目 | 数据 | |------|------| | 学习模式 | 随身听模式 | - 第一条')

    expect(html).toContain('<h1>Title</h1>')
    expect(html).toContain('<h2>1. Overview</h2>')
    expect(html).toContain('<table>')
    expect(html).toContain('<li>第一条</li>')
  })
})
