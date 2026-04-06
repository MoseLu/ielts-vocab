import type { PracticeStageGuideData } from './practiceStageGuide'

interface PracticeStageGuideProps {
  guide: PracticeStageGuideData
}

export default function PracticeStageGuide({ guide }: PracticeStageGuideProps) {
  return (
    <section className={`practice-stage-guide practice-stage-guide--${guide.tone}`} aria-label="关卡提示">
      <div className="practice-stage-guide__meta">
        <span className="practice-stage-guide__pill">{guide.levelLabel}</span>
        <span className="practice-stage-guide__pill">{guide.laneLabel}</span>
        <span className="practice-stage-guide__pill">{guide.phaseLabel}</span>
      </div>

      <div className="practice-stage-guide__headline">
        <span className="practice-stage-guide__eyebrow">关卡提示</span>
        <div className="practice-stage-guide__title">{guide.title}</div>
        <p className="practice-stage-guide__context">{guide.context}</p>
      </div>

      <dl className="practice-stage-guide__rows">
        {guide.rows.map(row => (
          <div key={row.label} className="practice-stage-guide__row">
            <dt className="practice-stage-guide__label">{row.label}</dt>
            <dd className="practice-stage-guide__value">{row.value}</dd>
          </div>
        ))}
      </dl>
    </section>
  )
}
