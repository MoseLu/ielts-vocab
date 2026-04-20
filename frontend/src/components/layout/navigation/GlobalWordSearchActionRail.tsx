import FavoriteToggleButton from '../../practice/FavoriteToggleButton'
import FeedbackIssueIcon from '../../ui/FeedbackIssueIcon'
import SlowPlaybackIcon from '../../ui/SlowPlaybackIcon'

interface GlobalWordSearchActionRailProps {
  favoriteActive: boolean
  favoritePending: boolean
  onToggleFavorite: () => void
  onPlaySlowWord: () => void
  onPlayWord: () => void
  onOpenFeedback: () => void
  word: string
}

export default function GlobalWordSearchActionRail({
  favoriteActive,
  favoritePending,
  onToggleFavorite,
  onPlaySlowWord,
  onPlayWord,
  onOpenFeedback,
  word,
}: GlobalWordSearchActionRailProps) {
  return (
    <div className="global-word-search-action-rail" aria-label="单词操作">
      <FavoriteToggleButton
        active={favoriteActive}
        pending={favoritePending}
        onClick={onToggleFavorite}
      />
      <button
        type="button"
        className="global-word-search-action-btn"
        aria-label={`朗读单词 ${word}`}
        title={`朗读单词 ${word}`}
        onClick={onPlayWord}
      >
        <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path
            d="M10.78 5.88a.9.9 0 0 1 1.47.7v10.84a.9.9 0 0 1-1.47.7l-3.8-3.05H4.9A1.4 1.4 0 0 1 3.5 13.67v-3.34a1.4 1.4 0 0 1 1.4-1.4h2.08l3.8-3.05Z"
            fill="currentColor"
          />
          <path
            d="M15.2 9.12a4.35 4.35 0 0 1 0 5.76"
            stroke="currentColor"
            strokeWidth="1.9"
            strokeLinecap="round"
          />
          <path
            d="M17.9 6.95a7.2 7.2 0 0 1 0 10.1"
            stroke="currentColor"
            strokeWidth="1.9"
            strokeLinecap="round"
          />
        </svg>
      </button>
      <button
        type="button"
        className="global-word-search-action-btn global-word-search-action-btn--slow"
        aria-label={`慢速朗读单词 ${word}`}
        title={`慢速朗读单词 ${word}`}
        onClick={onPlaySlowWord}
      >
        <SlowPlaybackIcon className="global-word-search-slow-icon" />
      </button>
      <button
        type="button"
        className="global-word-search-action-btn"
        aria-label={`反馈 ${word} 的问题`}
        title={`反馈 ${word} 的问题`}
        onClick={onOpenFeedback}
      >
        <FeedbackIssueIcon className="global-word-search-action-icon" />
      </button>
    </div>
  )
}
