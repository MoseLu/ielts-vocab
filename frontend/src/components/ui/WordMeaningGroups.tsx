import { parseWordMeaningGroups } from '../../lib/wordMeaning'

type WordMeaningGroupsProps = {
  className?: string
  definition: string | null | undefined
  pos: string | null | undefined
  size?: 'sm' | 'md' | 'lg'
}

function joinClassNames(parts: Array<string | null | undefined>): string {
  return parts.filter(Boolean).join(' ')
}

export default function WordMeaningGroups({
  className,
  definition,
  pos,
  size = 'md',
}: WordMeaningGroupsProps) {
  const groups = parseWordMeaningGroups({ pos, definition })
  if (groups.length === 0) return null

  const layoutClassName = groups.length > 1
    ? 'word-meaning-groups--stacked'
    : 'word-meaning-groups--inline'

  return (
    <div
      className={joinClassNames([
        'word-meaning-groups',
        layoutClassName,
        `word-meaning-groups--${size}`,
        className,
      ])}
    >
      {groups.map((group, index) => (
        <span
          key={`${group.posLabel}-${group.meaningText}-${index}`}
          className="word-meaning-group"
        >
          {group.posLabel ? (
            <span className="word-pos-tag word-meaning-group__pos">
              {group.posLabel}
              {group.meaningText ? ' ' : ''}
            </span>
          ) : null}
          {group.meaningText ? (
            <span className="word-meaning-group__text">{group.meaningText}</span>
          ) : null}
        </span>
      ))}
    </div>
  )
}
