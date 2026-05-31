import { useParams } from 'react-router-dom'
import GameCampaignPage from '../components/game/page/GameCampaignPage'

export const DEFAULT_GAME_THEME_ID = 'study-campus'

export function GameRouteElement({ surface }: { surface: 'map' | 'mission' }) {
  const { themeId } = useParams()
  return <GameCampaignPage surface={surface} themeId={themeId} />
}
