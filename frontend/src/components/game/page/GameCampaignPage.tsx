import { useMemo } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import GameMode from '../../practice/page/GameMode'

interface GameCampaignPageProps {
  surface?: 'map' | 'mission'
}

function normalizeOptionalParam(value: string | null): string | null {
  const normalized = value?.trim()
  return normalized || null
}

export default function GameCampaignPage({ surface = 'map' }: GameCampaignPageProps) {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const bookId = normalizeOptionalParam(searchParams.get('book'))
  const chapterId = normalizeOptionalParam(searchParams.get('chapter'))
  const dayValue = searchParams.get('day')
  const currentDay = useMemo(() => {
    if (!dayValue) return undefined
    const parsed = Number.parseInt(dayValue, 10)
    return Number.isInteger(parsed) && parsed > 0 ? parsed : undefined
  }, [dayValue])
  const missionPath = useMemo(() => {
    const query = searchParams.toString()
    return `/game/mission${query ? `?${query}` : ''}`
  }, [searchParams])
  const mapPath = useMemo(() => {
    const query = searchParams.toString()
    return `/game${query ? `?${query}` : ''}`
  }, [searchParams])

  return (
    <GameMode
      bookId={bookId}
      chapterId={chapterId}
      currentDay={currentDay}
      surface={surface}
      onBackToPlan={() => navigate('/plan')}
      onEnterMission={() => navigate(missionPath)}
      onExitToMap={() => navigate(mapPath)}
    />
  )
}
