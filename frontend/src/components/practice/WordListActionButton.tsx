const FAVORITE_ICON_PATH =
  'M707.584 93.184c-77.312 0-148.992 38.912-196.608 102.912-47.104-64-119.296-102.912-196.608-102.912-139.264 0-252.416 123.904-252.416 275.968 0 90.624 40.448 154.624 73.216 205.824C229.888 723.968 468.48 908.8 478.72 916.48c9.728 7.68 20.992 11.264 32.256 11.264s22.528-3.584 32.256-11.264c10.24-7.68 248.32-193.024 343.552-341.504 32.768-51.2 73.216-115.2 73.216-205.824 0-152.064-113.152-275.968-252.416-275.968zM821.76 573.44c-87.552 122.88-272.896 263.168-282.112 269.824-8.704 6.656-18.944 10.24-28.672 10.24-10.24 0-19.968-3.072-28.672-10.24-9.216-6.656-190.976-148.48-282.112-274.944-29.184-46.08-75.776-103.424-75.776-184.32 0-136.192 75.776-231.936 200.192-231.936 69.12 0 144.384 66.048 186.368 123.392 42.496-57.344 117.248-123.392 186.368-123.392 124.928 0 205.824 95.744 205.824 231.936 0 80.896-51.712 143.872-81.408 189.44z'

interface WordListActionButtonProps {
  kind: 'familiar' | 'favorite'
  active: boolean
  pending?: boolean
  onClick: () => void
}

function getButtonTitle(kind: 'familiar' | 'favorite', active: boolean, pending: boolean): string {
  if (pending) return kind === 'familiar' ? '正在更新熟字标记' : '正在更新收藏'
  if (kind === 'familiar') return active ? '取消熟字标记' : '标记为熟字'
  return active ? '移出收藏词书' : '收藏到收藏词书'
}

export default function WordListActionButton({
  kind,
  active,
  pending = false,
  onClick,
}: WordListActionButtonProps) {
  const title = getButtonTitle(kind, active, pending)

  return (
    <button
      type="button"
      className={`wordlist-action-btn wordlist-action-btn--${kind}${active ? ' is-active' : ''}${pending ? ' is-pending' : ''}`}
      onClick={event => {
        event.stopPropagation()
        onClick()
      }}
      onMouseDown={event => event.stopPropagation()}
      disabled={pending}
      aria-label={title}
      aria-pressed={active}
      title={title}
    >
      {kind === 'familiar' ? (
        <span className="wordlist-action-btn__label">熟字</span>
      ) : (
        <svg viewBox="0 0 1024 1024" aria-hidden="true">
          <path
            d={FAVORITE_ICON_PATH}
            fill={active ? 'currentColor' : 'none'}
            stroke="currentColor"
            strokeWidth="36"
            strokeLinejoin="round"
          />
        </svg>
      )}
    </button>
  )
}
