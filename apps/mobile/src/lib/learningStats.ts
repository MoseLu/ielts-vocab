type StatsRecord = Record<string, unknown>

function recordValue(value: unknown, key: string): StatsRecord {
  const next = value && typeof value === 'object' && !Array.isArray(value) ? (value as StatsRecord)[key] : null
  return next && typeof next === 'object' && !Array.isArray(next) ? next as StatsRecord : {}
}

function numberValue(record: StatsRecord, keys: string[]) {
  for (const key of keys) {
    const value = record[key]
    const number = typeof value === 'number' ? value : Number(value)
    if (Number.isFinite(number)) return number
  }
  return 0
}

export function todayMasteredWordsFromStats(stats: StatsRecord) {
  const alltime = recordValue(stats, 'alltime')
  const direct = numberValue(alltime, ['today_mastered_words', 'today_known_words', 'today_correct_words', 'today_words', 'today_total_words'])
  if (direct) return direct
  return numberValue(alltime, ['today_new_words']) + numberValue(alltime, ['today_review_words'])
}
