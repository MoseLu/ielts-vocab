import { useState } from 'react'
import type { FollowReadPronunciationResponse } from './followReadScoring'

interface FollowReadScoreDetailsProps {
  result: FollowReadPronunciationResponse
  label: string
  summary: string
}

const DIMENSION_LABELS = {
  phonemeAccuracy: '音素准确度',
  completeness: '完成度',
  fluency: '连贯性',
  prosody: '韵律参考',
} as const

function PhonemeChip({
  item,
}: {
  item: FollowReadPronunciationResponse['phonemeFeedback'][number]
}) {
  const candidates = item.candidatePhonemes
    .filter(candidate => candidate.phoneme && candidate.phoneme !== item.expectedPhoneme)
    .slice(0, 2)
  return (
    <div className={`follow-phoneme-detail is-${item.status}`}>
      <strong>/{item.expectedPhoneme}/</strong>
      <span>{Math.round(item.score)}</span>
      {candidates.length > 0 && (
        <small>
          可能读成 {candidates.map(candidate => `/${candidate.phoneme}/ ${Math.round(candidate.confidence)}`).join('、')}
        </small>
      )}
    </div>
  )
}

export default function FollowReadScoreDetails({
  result,
  label,
  summary,
}: FollowReadScoreDetailsProps) {
  const [expanded, setExpanded] = useState(false)
  const phonemeFeedback = result.phonemeFeedback || []
  const canExpand = phonemeFeedback.length > 0
  const dimensions = result.dimensions

  return (
    <div className={`follow-score-card follow-score-card--${result.band}`} role="status" aria-live="polite">
      <button
        type="button"
        className="follow-score-card__summary"
        onClick={() => canExpand && setExpanded(current => !current)}
        aria-expanded={canExpand ? expanded : undefined}
      >
        <span className="follow-score-card__header">
          <strong>{Math.round(result.score)}</strong>
          <span>{label}</span>
        </span>
        <span className="follow-score-card__text">{summary}</span>
        {canExpand && <small>{expanded ? '收起逐音素详情' : '点击查看逐音素详情'}</small>}
      </button>
      {expanded && (
        <div className="follow-score-details">
          {dimensions && (
            <div className="follow-score-dimensions">
              {Object.entries(dimensions).map(([key, value]) => (
                <span key={key}>
                  {DIMENSION_LABELS[key as keyof typeof DIMENSION_LABELS]} {Math.round(value)}
                </span>
              ))}
            </div>
          )}
          <div className="follow-phoneme-details">
            {phonemeFeedback.map((item, index) => (
              <PhonemeChip key={`${item.expectedPhoneme}-${index}`} item={item} />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
