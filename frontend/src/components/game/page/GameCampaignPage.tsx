import { useMemo } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import GameMode from '../../practice/page/GameMode'

function normalizeOptionalParam(value: string | null): string | null {
  const normalized = value?.trim()
  return normalized || null
}

export default function GameCampaignPage() {
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

  return (
    <GameMode
      bookId={bookId}
      chapterId={chapterId}
      currentDay={currentDay}
      onBackToPlan={() => navigate('/plan')}
    />
  )
}
