import { useMemo } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import GameMode from '../../practice/page/GameMode'
import GameThemeSelectPage from './GameThemeSelectPage'
import type { GameCampaignDimension } from '../../../lib'

interface GameCampaignPageProps {
  surface?: 'themes' | 'map' | 'mission'
  themeId?: string
}

function normalizeOptionalParam(value: string | null): string | null {
  const normalized = value?.trim()
  return normalized || null
}

function normalizeGameDimension(value: string | null): GameCampaignDimension | null {
  const normalized = normalizeOptionalParam(value)
  return normalized && ['recognition', 'meaning', 'dictation', 'speaking', 'listening'].includes(normalized)
    ? normalized as GameCampaignDimension
    : null
}

export default function GameCampaignPage({ surface = 'themes', themeId }: GameCampaignPageProps) {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const bookId = normalizeOptionalParam(searchParams.get('book'))
  const chapterId = normalizeOptionalParam(searchParams.get('chapter'))
  const selectedThemeId = normalizeOptionalParam(themeId ?? searchParams.get('themeId'))
  const themeChapterId = normalizeOptionalParam(searchParams.get('themeChapter') ?? searchParams.get('themeChapterId'))
  const task = normalizeOptionalParam(searchParams.get('task'))
  const taskDimension = normalizeGameDimension(searchParams.get('dimension'))
  const dayValue = searchParams.get('day')
  const currentDay = useMemo(() => {
    if (!dayValue) return undefined
    const parsed = Number.parseInt(dayValue, 10)
    return Number.isInteger(parsed) && parsed > 0 ? parsed : undefined
  }, [dayValue])
  const themeMapBasePath = selectedThemeId ? `/game/themes/${selectedThemeId}` : '/game'
  const missionPath = useMemo(() => {
    const query = searchParams.toString()
    return selectedThemeId
      ? `${themeMapBasePath}/mission${query ? `?${query}` : ''}`
      : `/game/mission${query ? `?${query}` : ''}`
  }, [searchParams, selectedThemeId, themeMapBasePath])
  const mapPath = useMemo(() => {
    const query = searchParams.toString()
    return selectedThemeId
      ? `${themeMapBasePath}${query ? `?${query}` : ''}`
      : `/game${query ? `?${query}` : ''}`
  }, [searchParams, selectedThemeId, themeMapBasePath])

  if (surface === 'themes') {
    return <GameThemeSelectPage onSelectTheme={theme => navigate(`/game/themes/${theme.id}`)} />
  }

  return (
    <GameMode
      bookId={bookId}
      chapterId={chapterId}
      currentDay={currentDay}
      surface={surface}
      themeId={selectedThemeId}
      themeChapterId={themeChapterId}
      task={task}
      taskDimension={taskDimension}
      onBackToPlan={() => navigate('/plan')}
      onEnterMission={() => navigate(missionPath)}
      onExitToMap={() => navigate(mapPath)}
      onSelectThemeChapter={(nextChapterId, page) => {
        const nextParams = new URLSearchParams(searchParams)
        nextParams.set('themeChapter', nextChapterId)
        nextParams.set('page', String(page))
        navigate(`${themeMapBasePath}?${nextParams.toString()}`)
      }}
    />
  )
}
