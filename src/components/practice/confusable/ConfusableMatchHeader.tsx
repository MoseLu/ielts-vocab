import Popover from '../../ui/Popover'
import { Scrollbar } from '../../ui/Scrollbar'
import type { Chapter } from '../types'
import type { MatchCard } from '../confusableMatch'
import { getSelectionHint } from './confusableMatchPageHelpers'

interface ConfusableMatchHeaderProps {
  bookId: string
  chapterId: string | null
  currentChapterTitle: string
  bookChapters: Chapter[]
  supportsCustomGroups: boolean
  selectedCard: MatchCard | null
  answeredCount: number
  totalWords: number
  correctCount: number
  wrongCount: number
  onOpenCustomModal: () => void
  onNavigate: (path: string) => void
  buildChapterPath: (chapterId: string | number) => string
}

export function ConfusableMatchHeader({
  bookId,
  chapterId,
  currentChapterTitle,
  bookChapters,
  supportsCustomGroups,
  selectedCard,
  answeredCount,
  totalWords,
  correctCount,
  wrongCount,
  onOpenCustomModal,
  onNavigate,
  buildChapterPath,
}: ConfusableMatchHeaderProps) {
  return (
    <>
      <div className="practice-ctrl-bar confusable-ctrl-bar">
        <button
          type="button"
          className="practice-ctrl-brand"
          onClick={() => onNavigate('/books')}
          title="返回词书"
        >
          <img
            src="/images/logo.png"
            alt="Logo"
            className="practice-ctrl-brand-logo"
            onError={event => { event.currentTarget.style.display = 'none' }}
          />
          <span className="practice-ctrl-brand-text">易混辨析</span>
        </button>

        <div className="practice-ctrl-right">
          {supportsCustomGroups && (
            <button type="button" className="confusable-toolbar-btn" onClick={onOpenCustomModal}>
              自定义组
            </button>
          )}

          <Popover
            placement="bottom"
            offset={10}
            panelClassName="popover-ctx-panel"
            trigger={(
              <button className="practice-ctrl-icon-btn practice-mode-btn" title="切换章节">
                <span className="practice-mode-label">{currentChapterTitle || '选择章节'}</span>
                <svg className="practice-ctx-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="6 9 12 15 18 9" />
                </svg>
              </button>
            )}
          >
            <Scrollbar className="popover-ctx-scroll" maxHeight={320}>
              {bookChapters.map(chapter => (
                <button
                  key={chapter.id}
                  className={`popover-option ${String(chapter.id) === String(chapterId) ? 'active' : ''}`}
                  onClick={() => onNavigate(buildChapterPath(chapter.id))}
                >
                  <span className={`ctx-radio ${String(chapter.id) === String(chapterId) ? 'checked' : ''}`} />
                  {chapter.title}
                </button>
              ))}
            </Scrollbar>
          </Popover>

          <div className="confusable-progress-chip">
            <strong>{answeredCount}</strong>
            <span>/ {totalWords} 已消除</span>
          </div>
        </div>
      </div>

      <div className="confusable-stage-header">
        <div>
          <h1 className="confusable-title">{currentChapterTitle || '易混词辨析'}</h1>
          <p className="confusable-subtitle">
            每个小棋盘就是一组易混词。先点英文，再点中文，组内连线成功后就会像消消乐一样消失。
          </p>
        </div>
        <div className="confusable-stats">
          <span className="confusable-stat confusable-stat--ok">成功 {correctCount}</span>
          <span className="confusable-stat confusable-stat--bad">误连 {wrongCount}</span>
        </div>
      </div>

      <div className={`confusable-selection-tray ${selectedCard ? 'is-active' : ''}`}>
        <div>
          <span className="confusable-selection-label">当前连线</span>
          <strong>{selectedCard ? '已选中一张卡片' : '从任意小棋盘开始'}</strong>
          <span>{getSelectionHint(selectedCard)}</span>
        </div>
        {selectedCard && (
          <span className={`confusable-selection-token confusable-selection-token--${selectedCard.side}`}>
            {selectedCard.side === 'word' ? `EN · ${selectedCard.label}` : `中 · ${selectedCard.label}`}
          </span>
        )}
      </div>
    </>
  )
}
