import type { WrongWordCollectionScope } from '../../../features/vocabulary/wrongWordsStore'
import { Card } from '../../ui'
import { buildErrorBookOverview } from './errorsPageProgress'

interface ErrorsOverviewProps {
  scope: WrongWordCollectionScope
}

export function ErrorsOverview({ scope }: ErrorsOverviewProps) {
  const overview = buildErrorBookOverview(scope)

  return (
    <section className="errors-overview" aria-label="错词流转总览">
      <Card className="errors-overview-card" padding="md">
        <div className="errors-overview-head">
          <div>
            <p className="errors-overview-eyebrow">错词流转</p>
            <h2 className="errors-overview-title">错词按这个顺序推进</h2>
          </div>
          <span className="errors-overview-focus">{overview.focusLabel}</span>
        </div>

        <div className="errors-journey-track" aria-hidden="true">
          {overview.steps.map((step, index) => {
            const stateClassName = index < overview.activeIndex
              ? ' is-complete'
              : (index === overview.activeIndex ? ' is-active' : '')

            return (
              <span
                key={step.label}
                className={`errors-journey-segment errors-journey-segment--${step.tone}${stateClassName}`}
              />
            )
          })}
        </div>

        <div className="errors-journey-labels">
          {overview.steps.map((step, index) => {
            const isActive = index === overview.activeIndex
            return (
              <div
                key={step.label}
                className={`errors-journey-label${isActive ? ' is-active' : ''}`}
                title={step.detail}
              >
                <span className="errors-journey-step">{step.step}</span>
                <strong>{step.label}</strong>
              </div>
            )
          })}
        </div>
      </Card>
    </section>
  )
}
