import Popover from '../../ui/Popover'
import { Scrollbar } from '../../ui/Scrollbar'
import { staticAssetUrl } from '../../../lib/staticAssetUrl'
import { PRACTICE_WORD_LIST_ICON_PATH } from '../controlIcons'
import type { Chapter } from '../types'

const HOME_ICON_PATH = 'M3 10.5 12 3l9 7.5M5 9.5V21h5.5v-6.5h3V21H19V9.5'

function formatCustomConfusableTitle(title: string): string {
  const trimmed = title.trim()
  const match = trimmed.match(/^自定义易混组\s*(\d+)/)
  if (!match) return trimmed
  return `自定义易混${Number(match[1])}`
}

function formatChapterTitle(title: string): string {
  return formatCustomConfusableTitle(title || '选择章节')
}

interface ConfusableMatchHeaderProps {
  chapterId: string | null
  currentChapterTitle: string
  bookChapters: Chapter[]
  canEditCurrentChapter: boolean
  showWordList: boolean
  onEditCurrentChapter: () => void
  onWordListToggle: () => void
  onExitHome: () => void
  onNavigate: (path: string) => void
  buildChapterPath: (chapterId: string | number) => string
}

export function ConfusableMatchHeader({
  chapterId,
  currentChapterTitle,
  bookChapters,
  canEditCurrentChapter,
  showWordList,
  onEditCurrentChapter,
  onWordListToggle,
  onExitHome,
  onNavigate,
  buildChapterPath,
}: ConfusableMatchHeaderProps) {
  const displayTitle = formatChapterTitle(currentChapterTitle || '选择章节')

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
            src={staticAssetUrl('/images/logo.png')}
            alt="Logo"
            className="practice-ctrl-brand-logo"
            onError={event => { event.currentTarget.style.display = 'none' }}
          />
          <span className="practice-ctrl-brand-text">易混辨析</span>
        </button>

        <div className="practice-ctrl-right">
          {canEditCurrentChapter && (
            <button
              type="button"
              className="practice-ctrl-icon-btn practice-mode-btn"
              onClick={onEditCurrentChapter}
              title="编辑当前组"
            >
              <span className="practice-mode-label">编辑当前组</span>
            </button>
          )}

          <Popover
            placement="bottom"
            offset={10}
            panelClassName="popover-ctx-panel"
            trigger={(
              <button className="practice-ctrl-icon-btn practice-mode-btn" title="切换章节">
                <span className="practice-mode-label">{displayTitle}</span>
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
                  {formatChapterTitle(chapter.title)}
                </button>
              ))}
            </Scrollbar>
          </Popover>

          <button
            className={`practice-ctrl-icon-btn ${showWordList ? 'active' : ''}`}
            onClick={onWordListToggle}
            title="单词列表"
            aria-label="单词列表"
          >
            <svg viewBox="0 0 1024 1024" fill="currentColor" width="18" height="18" aria-hidden="true">
              <path d={PRACTICE_WORD_LIST_ICON_PATH} />
            </svg>
          </button>

          <button
            className="practice-ctrl-icon-btn"
            onClick={onExitHome}
            title="返回主页"
            aria-label="返回主页"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
              <path d={HOME_ICON_PATH} strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
        </div>
      </div>
    </>
  )
}
