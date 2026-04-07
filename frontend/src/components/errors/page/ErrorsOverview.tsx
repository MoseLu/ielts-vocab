import { useMemo } from 'react'
import type { WrongWordRecord } from '../../../features/vocabulary/wrongWordsStore'
import { Card } from '../../ui'
import { buildErrorBookOverview } from './errorsPageProgress'

interface ErrorsOverviewProps {
  words: WrongWordRecord[]
}

export function ErrorsOverview({ words }: ErrorsOverviewProps) {
  const overview = useMemo(() => buildErrorBookOverview(words), [words])

  return (
    <section className="errors-overview" aria-label="错词流转总览">
      <div className="errors-overview-head">
        <div>
          <p className="errors-overview-eyebrow">错词流转</p>
          <h2 className="errors-overview-title">现在每个错词走到哪一步</h2>
        </div>
        <p className="errors-overview-caption">
          错词不会直接消失。它会先从“待清”里毕业，再继续走后面的长期复习，所以这里把整个过程拆开给你看。
        </p>
      </div>

      <div className="errors-journey-grid">
        {overview.journeyCards.map(card => (
          <Card key={card.title} className={`errors-journey-card errors-journey-card--${card.tone}`} padding="md">
            <div className="errors-journey-step">{card.step}</div>
            <div className="errors-journey-title">{card.title}</div>
            <div className="errors-journey-value">{card.value}</div>
            <div className="errors-journey-detail">{card.detail}</div>
          </Card>
        ))}
      </div>

      <div className="errors-spotlight-grid">
        {overview.spotlightCards.map(card => (
          <Card key={card.label} className="errors-spotlight-card" padding="md">
            <div className="errors-spotlight-label">{card.label}</div>
            <div className="errors-spotlight-value">{card.value}</div>
            <div className="errors-spotlight-detail">{card.detail}</div>
          </Card>
        ))}
      </div>
    </section>
  )
}
