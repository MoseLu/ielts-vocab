const RADIUS = 20
const CIRCUMFERENCE = 2 * Math.PI * RADIUS

export function QuickMemoryCountdownRing({
  seconds,
  total,
}: {
  seconds: number
  total: number
}) {
  const progress = seconds / total
  const dash = progress * CIRCUMFERENCE

  return (
    <svg className="qm-timer-svg" viewBox="0 0 48 48" width="48" height="48">
      <circle className="qm-timer-track" cx="24" cy="24" r={RADIUS} fill="none" strokeWidth="3" />
      <circle
        className={`qm-timer-progress${seconds <= 1 ? ' is-critical' : ''}`}
        cx="24"
        cy="24"
        r={RADIUS}
        fill="none"
        strokeWidth="3"
        strokeDasharray={`${dash} ${CIRCUMFERENCE}`}
        strokeLinecap="round"
        transform="rotate(-90 24 24)"
      />
      <text
        className={`qm-timer-label${seconds <= 1 ? ' is-critical' : ''}`}
        x="24"
        y="24"
        dominantBaseline="central"
        textAnchor="middle"
        fontSize="14"
        fontWeight="700"
      >
        {seconds}
      </text>
    </svg>
  )
}
