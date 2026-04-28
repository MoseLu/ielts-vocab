import { useEffect, useState } from 'react'
import { fetchGameThemeCatalog } from '../../../lib/gamePractice'
import type { GameThemeCatalog, GameThemeSummary } from '../../../lib'

interface GameThemeSelectPageProps {
  onSelectTheme: (theme: GameThemeSummary) => void
}

function formatCount(value: number): string {
  return Math.max(0, value).toLocaleString('zh-CN')
}

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
  const backdrop = catalog.themes[0]?.assets.desktopMap || catalog.themes[0]?.assets.selectCard || ''

  return (
    <section className="game-theme-select" aria-label="IELTS 主题战役">
      {backdrop ? <img className="game-theme-select__backdrop" src={backdrop} alt="" aria-hidden="true" /> : null}
      <header className="game-theme-select__header">
        <span>IELTS 五维闯关</span>
        <h1>选择主题地图</h1>
        <strong>{formatCount(catalog.totalWords)} words</strong>
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
            <img
              className="game-theme-select__card-map"
              src={theme.assets.selectCard || theme.assets.desktopMap}
              alt=""
              aria-hidden="true"
            />
            <span className="game-theme-select__badge" aria-hidden="true">
              {index + 1}
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
              <span>进入</span>
            </span>
          </button>
        ))}
      </div>
    </section>
  )
}
