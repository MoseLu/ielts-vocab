import type { AppSettings, Chapter, PracticeMode, PracticePageProps, Word } from './types'
import PracticePageContainer from './PracticePageContainer'

export type { PracticeMode, Word, AppSettings, Chapter }

function PracticePage(props: PracticePageProps) {
  return <PracticePageContainer {...props} />
}

export default PracticePage
