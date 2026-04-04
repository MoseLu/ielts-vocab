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
      <circle cx="24" cy="24" r={RADIUS} fill="none" stroke="var(--border)" strokeWidth="3" />
      <circle
        cx="24"
        cy="24"
        r={RADIUS}
        fill="none"
        stroke={seconds <= 1 ? 'var(--error)' : 'var(--accent)'}
        strokeWidth="3"
        strokeDasharray={`${dash} ${CIRCUMFERENCE}`}
        strokeLinecap="round"
        transform="rotate(-90 24 24)"
        style={{ transition: 'stroke-dasharray 0.9s linear, stroke 0.2s' }}
      />
      <text
        x="24"
        y="24"
        dominantBaseline="central"
        textAnchor="middle"
        fontSize="14"
        fontWeight="700"
        fill={seconds <= 1 ? 'var(--error)' : 'var(--text-primary)'}
      >
        {seconds}
      </text>
    </svg>
  )
}
