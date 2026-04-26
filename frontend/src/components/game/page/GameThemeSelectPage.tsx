import { useEffect, useState } from 'react'
import { fetchGameThemeCatalog } from '../../../lib/gamePractice'
import type { GameThemeCatalog, GameThemeSummary } from '../../../lib'
import { prdMapBackgroundForTheme } from '../../practice/page/game-mode/GamePrdUi'
import { prdUiAsset } from '../../practice/page/game-mode/prdUiAssets'

interface GameThemeSelectPageProps {
  onSelectTheme: (theme: GameThemeSummary) => void
}

function formatCount(value: number): string {
  return Math.max(0, value).toLocaleString('zh-CN')
}

const THEME_ICON_ASSETS = [
  prdUiAsset.icons.book,
  prdUiAsset.icons.bag,
  prdUiAsset.icons.sound,
  prdUiAsset.icons.task,
  prdUiAsset.icons.pen,
  prdUiAsset.icons.achievement,
  prdUiAsset.icons.microphone,
  prdUiAsset.icons.rank,
] as const

export default function GameThemeSelectPage({ onSelectTheme }: GameThemeSelectPageProps) {
  const [catalog, setCatalog] = useState<GameThemeCatalog | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setIsLoading(true)
    setError(null)
    fetchGameThemeCatalog().then(nextCatalog => {
      if (!cancelled) setCatalog(nextCatalog)
    }).catch(loadError => {
      if (!cancelled) setError(loadError instanceof Error ? loadError.message : '主题地图加载失败')
    }).finally(() => {
      if (!cancelled) setIsLoading(false)
    })
    return () => {
      cancelled = true
    }
  }, [])

  if (isLoading) {
    return <section className="game-theme-select is-loading">正在载入主题地图...</section>
  }

  if (error || !catalog) {
    return <section className="game-theme-select is-error">{error ?? '主题地图加载失败'}</section>
  }

  return (
    <section className="game-theme-select" aria-label="IELTS 主题战役">
      <img
        className="game-theme-select__backdrop"
        src={prdMapBackgroundForTheme('study-campus')}
        alt=""
        aria-hidden="true"
      />
      <header className="game-theme-select__header">
        <img src={prdUiAsset.modal.parchmentTitle} alt="" aria-hidden="true" />
        <span>IELTS 五维闯关</span>
        <h1>选择主题地图</h1>
        <strong>
          <img src={prdUiAsset.icons.book} alt="" aria-hidden="true" />
          {formatCount(catalog.totalWords)} words
        </strong>
      </header>
      <div className="game-theme-select__grid">
        {catalog.themes.map((theme, index) => (
          <button
            key={theme.id}
            type="button"
            className="game-theme-select__card"
            data-theme={theme.id}
            onClick={() => onSelectTheme(theme)}
          >
            <img className="game-theme-select__card-map" src={prdMapBackgroundForTheme(theme.id)} alt="" aria-hidden="true" />
            <span className="game-theme-select__badge" aria-hidden="true">
              <img src={prdUiAsset.map.levelBadgeBlue} alt="" />
              <img src={THEME_ICON_ASSETS[index % THEME_ICON_ASSETS.length]} alt="" />
            </span>
            <span className="game-theme-select__card-copy">
              <strong>{theme.title}</strong>
              <span>{theme.subtitle}</span>
            </span>
            <span className="game-theme-select__card-meta">
              <span>{formatCount(theme.wordCount)} words</span>
              <span>{formatCount(theme.totalChapters)} chapters</span>
            </span>
            <span className="game-theme-select__action">
              <img src={prdUiAsset.buttons.green} alt="" aria-hidden="true" />
              <span>进入</span>
            </span>
          </button>
        ))}
      </div>
    </section>
  )
}
