import type { SummaryGenerationJob } from '../../../lib/schemas'

export function today(): string {
  return new Date().toISOString().slice(0, 10)
}

export function formatDateTime(iso: string): string {
  if (!iso) return ''
  const date = new Date(iso)
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}

export function toPlainTextSnippet(text: string, maxLen = 120): string {
  const plain = text
    .replace(/\r\n/g, '\n')
    .replace(/[`#>*_|-]+/g, ' ')
    .replace(/\[(.*?)\]\((.*?)\)/g, '$1')
    .replace(/\s+/g, ' ')
    .trim()

  if (plain.length <= maxLen) return plain
  return `${plain.slice(0, maxLen).trim()}...`
}

export function isActiveSummaryJob(job: SummaryGenerationJob | null): job is SummaryGenerationJob {
  return Boolean(job && (job.status === 'queued' || job.status === 'running'))
}
