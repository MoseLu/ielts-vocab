import { describe, expect, it } from 'vitest'
import { normalizeAIResponseMarkdown, renderAIResponseMarkdown } from './aiMarkdown'

describe('aiMarkdown', () => {
  it('renders assistant lists, links, tables and inline code as rich markdown', () => {
    const html = renderAIResponseMarkdown(`看完了，范围如下：

- [ielts_reading_premium.json](/books/reading)：3375 条
- [ielts_listening_premium.json](/books/listening)：3894 条

| 口径 | Reading | Listening | 合并去重 |
|---|---:|---:|---:|
| 定义里明确写“复数” | 261 | 352 | 494 |

先修 \`metres\` 和 \`images\`。`)

    expect(html).toContain('<ul>')
    expect(html).toContain('<a href="/books/reading">ielts_reading_premium.json</a>')
    expect(html).toContain('<table>')
    expect(html).toContain('<th>Reading</th>')
    expect(html).toContain('<td>494</td>')
    expect(html).toContain('<code>metres</code>')
  })

  it('restores compressed table rows without splitting the table block', () => {
    const normalized = normalizeAIResponseMarkdown('范围： | A | B | |---|---| | 1 | 2 | 结论：继续')

    expect(normalized).toContain('范围：\n\n| A | B |\n|---|---|\n| 1 | 2 |\n\n结论：继续')
    expect(renderAIResponseMarkdown(normalized)).toContain('<table>')
  })

  it('unwraps full-message markdown fences while preserving inner code fences', () => {
    const normalized = normalizeAIResponseMarkdown(`\`\`\`markdown
# 标题

\`\`\`ts
const value = "- not a list"
\`\`\`
\`\`\``)

    expect(normalized.startsWith('# 标题')).toBe(true)
    expect(normalized).toContain('```ts\nconst value = "- not a list"\n```')
  })

  it('strips unsafe html from assistant output', () => {
    const html = renderAIResponseMarkdown('正常内容<script>alert(1)</script><img src=x onerror=alert(1)>')

    expect(html).toContain('正常内容')
    expect(html).not.toContain('<script')
    expect(html).not.toContain('<img')
    expect(html).not.toContain('onerror')
  })
})
