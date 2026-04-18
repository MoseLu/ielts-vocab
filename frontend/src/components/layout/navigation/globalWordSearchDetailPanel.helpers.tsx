import { Fragment } from 'react'

export type DetailTab = 'examples' | 'root' | 'english' | 'derivatives' | 'notes'
export type NoteStatus = 'idle' | 'saving' | 'saved' | 'error'

export const DETAIL_TABS: Array<{ id: DetailTab; label: string }> = [
  { id: 'examples', label: '例句' },
  { id: 'root', label: '词根' },
  { id: 'english', label: '英义' },
  { id: 'derivatives', label: '派生' },
  { id: 'notes', label: '笔记' },
]

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

export function renderHighlightedText(text: string, query: string) {
  const trimmedQuery = query.trim()
  if (!trimmedQuery) return text

  const segments = text.split(new RegExp(`(${escapeRegExp(trimmedQuery)})`, 'ig'))
  return segments.map((segment, index) => (
    <Fragment key={`${segment}-${index}`}>
      {segment.toLowerCase() === trimmedQuery.toLowerCase() ? (
        <mark className="global-word-search-highlight">{segment}</mark>
      ) : (
        segment
      )}
    </Fragment>
  ))
}

export function buildNoteStatusLabel(status: NoteStatus): string {
  if (status === 'saving') return '自动保存中...'
  if (status === 'saved') return '已保存到账号'
  if (status === 'error') return '保存失败，请稍后重试'
  return '自动保存到当前账号'
}
