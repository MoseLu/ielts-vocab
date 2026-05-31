import React, { useEffect, useMemo, useState } from 'react'
import { StyleSheet, Text, View } from 'react-native'
import { PRACTICE_MODE_LABELS } from '@ielts-vocab/app-core'
import { loadLearnerProfile, loadLearningStats } from '../api/learnerApi'
import { Card, Heading, Meta, ScreenScroll, StatusText } from '../components/primitives'
import { theme } from '../theme'

type AnyRecord = Record<string, unknown>
const chartColors = ['#FF7E36', '#45C48A', '#55A6FF', '#8B7CF6', '#F36B9A', '#F59E0B', '#14B8A6']

function recordValue(source: AnyRecord | undefined, key: string): AnyRecord {
  const value = source?.[key]
  return value && typeof value === 'object' && !Array.isArray(value) ? value as AnyRecord : {}
}
function numberValue(source: AnyRecord | undefined, keys: string[]): number {
  for (const key of keys) {
    const value = source?.[key]
    if (typeof value === 'number' && Number.isFinite(value)) return value
    if (typeof value === 'string' && value.trim()) return Number(value) || 0
  }
  return 0
}

function arrayValue(source: AnyRecord | undefined, key: string): AnyRecord[] {
  const value = source?.[key]
  return Array.isArray(value) ? value.filter((item): item is AnyRecord => !!item && typeof item === 'object') : []
}

function fmtInt(value: number): string {
  return String(Math.max(0, Math.round(value)))
}

function fmtDuration(seconds: number): string {
  if (!seconds) return '0 分钟'
  if (seconds < 60) return `${Math.round(seconds)} 秒`
  if (seconds < 3600) return `${Math.round(seconds / 60)} 分钟`
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.round((seconds % 3600) / 60)
  return minutes ? `${hours} 小时 ${minutes} 分钟` : `${hours} 小时`
}

function fmtPct(value: number): string {
  if (!value) return '0%'
  const normalized = value > 0 && value <= 1 ? value * 100 : value
  return `${Math.round(normalized)}%`
}

function labelForMode(value: unknown): string {
  const mode = String(value ?? '')
  return PRACTICE_MODE_LABELS[mode as keyof typeof PRACTICE_MODE_LABELS] || mode || '练习'
}

function shortDate(value: unknown): string {
  const text = String(value ?? '')
  return text.length >= 10 ? text.slice(5, 10) : text || '--'
}

function SummaryMetric({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.metricCard}>
      <Text style={styles.metricValue}>{value}</Text>
      <Text style={styles.metricLabel}>{label}</Text>
    </View>
  )
}

function DailyChart({ rows }: { rows: AnyRecord[] }) {
  const data = rows.slice(-7)
  const maxWords = Math.max(1, ...data.map(item => numberValue(item, ['words_studied', 'words', 'total_words'])))
  if (!data.length) return <Meta>完成练习后会生成每日学习记录。</Meta>
  return (
    <View style={styles.dailyChart}>
      {data.map((item, index) => {
        const words = numberValue(item, ['words_studied', 'words', 'total_words'])
        return (
          <View key={`${String(item.date)}-${index}`} style={styles.dailyColumn}>
            <Text style={styles.dailyValue}>{fmtInt(words)}</Text>
            <View style={styles.dailyBarWrap}>
              <View style={[styles.dailyBar, { height: `${Math.max(8, (words / maxWords) * 100)}%` }]} />
            </View>
            <Text style={styles.dailyDate}>{shortDate(item.date)}</Text>
          </View>
        )
      })}
    </View>
  )
}

function ModeChart({ modeBreakdown, pieChart }: { modeBreakdown: AnyRecord[]; pieChart: AnyRecord[] }) {
  const rows = (pieChart.length ? pieChart : modeBreakdown).slice(0, 7)
  const total = rows.reduce((sum, item) => sum + numberValue(item, ['value', 'words_studied', 'attempts', 'sessions']), 0)
  if (!rows.length || !total) return <Meta>完成练习后会生成模式占比。</Meta>
  return (
    <>
      <View style={styles.stackBar}>
        {rows.map((item, index) => {
          const value = numberValue(item, ['value', 'words_studied', 'attempts', 'sessions'])
          return <View key={`${String(item.mode)}-${index}`} style={[styles.stackSlice, { backgroundColor: chartColors[index % chartColors.length], flex: Math.max(1, value) }]} />
        })}
      </View>
      {modeBreakdown.slice(0, 7).map((item, index) => (
        <View key={`${String(item.mode)}-legend-${index}`} style={styles.legendRow}>
          <View style={[styles.legendDot, { backgroundColor: chartColors[index % chartColors.length] }]} />
          <Text style={styles.legendName}>{labelForMode(item.mode)}</Text>
          <Text style={styles.legendValue}>
            {fmtInt(numberValue(item, ['words_studied', 'value']))} 词 · {fmtPct(numberValue(item, ['accuracy']))}
          </Text>
        </View>
      ))}
    </>
  )
}

function ChapterChart({ rows }: { rows: AnyRecord[] }) {
  const data = rows.slice(0, 6)
  const maxWords = Math.max(1, ...data.map(item => numberValue(item, ['words_learned', 'words_studied', 'correct'])))
  if (!data.length) return <Meta>章节练习完成后会显示章节分布。</Meta>
  return (
    <View style={styles.chapterList}>
      {data.map((item, index) => {
        const words = numberValue(item, ['words_learned', 'words_studied', 'correct'])
        const title = String(item.chapter_title ?? item.book_title ?? `Chapter ${index + 1}`)
        return (
          <View key={`${title}-${index}`} style={styles.chapterRow}>
            <Text numberOfLines={1} style={styles.chapterName}>{title}</Text>
            <View style={styles.chapterTrack}>
              <View style={[styles.chapterFill, { width: `${Math.max(5, (words / maxWords) * 100)}%` }]} />
            </View>
            <Text style={styles.chapterValue}>{fmtInt(words)}</Text>
          </View>
        )
      })}
    </View>
  )
}

function EbbinghausChart({ alltime }: { alltime: AnyRecord }) {
  const stages = arrayValue(alltime, 'ebbinghaus_stages')
  const data = stages.length ? stages : [1, 1, 4, 7, 14, 30].map((days, stage) => ({ actual_pct: 0, interval_days: days, stage }))
  return (
    <View style={styles.stageList}>
      {data.map((item, index) => {
        const value = numberValue(item, ['actual_pct'])
        return (
          <View key={`${String(item.stage)}-${index}`} style={styles.stageRow}>
            <Text style={styles.stageName}>{numberValue(item, ['interval_days'])}天</Text>
            <View style={styles.stageTrack}>
              <View style={[styles.stageFill, { width: `${Math.max(4, Math.min(100, value))}%` }]} />
            </View>
            <Text style={styles.stageValue}>{fmtPct(value)}</Text>
          </View>
        )
      })}
    </View>
  )
}

function ProfileRow({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.profileRow}>
      <Text style={styles.profileLabel}>{label}</Text>
      <Text style={styles.profileValue}>{value || '暂无'}</Text>
    </View>
  )
}

export function StatsScreen() {
  const [stats, setStats] = useState<AnyRecord>({})
  const [profile, setProfile] = useState<AnyRecord>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([loadLearningStats(), loadLearnerProfile()])
      .then(([nextStats, nextProfile]) => {
        setStats(nextStats)
        setProfile(nextProfile)
      })
      .catch(err => setError(err instanceof Error ? err.message : '统计加载失败'))
      .finally(() => setLoading(false))
  }, [])

  const summary = recordValue(stats, 'summary')
  const alltime = recordValue(stats, 'alltime')
  const daily = arrayValue(stats, 'daily')
  const modeBreakdown = arrayValue(stats, 'mode_breakdown')
  const pieChart = arrayValue(stats, 'pie_chart')
  const chapterBreakdown = arrayValue(stats, 'chapter_breakdown')
  const profileSummary = recordValue(profile, 'summary')
  const focusWords = arrayValue(profile, 'focus_words').slice(0, 8)
  const repeatedTopics = arrayValue(profile, 'repeated_topics').slice(0, 4)

  const todayNew = numberValue(alltime, ['today_new_words'])
  const todayReview = numberValue(alltime, ['today_review_words'])
  const todayWords = numberValue(alltime, ['today_words', 'today_total_words']) || todayNew + todayReview
  const todayAccuracy = numberValue(alltime, ['today_accuracy']) || numberValue(profileSummary, ['today_accuracy'])
  const totalLearned = numberValue(alltime, ['total_words', 'learned_words']) || numberValue(summary, ['learned_words'])
  const totalReviewed = numberValue(alltime, ['alltime_review_words', 'total_review_words'])
  const streakDays = numberValue(profileSummary, ['streak_days']) || numberValue(alltime, ['streak_days'])
  const totalSessions = useMemo(
    () => modeBreakdown.reduce((sum, item) => sum + numberValue(item, ['sessions']), 0) || numberValue(summary, ['total_sessions']),
    [modeBreakdown, summary],
  )

  return (
    <ScreenScroll hideHeader title="学习统计">
      <StatusText error={error} loading={loading} />
      <Card>
        <View style={styles.sectionHead}>
          <View>
            <Meta>Web 同源指标</Meta>
            <Heading>学习概览</Heading>
          </View>
        </View>
        <View style={styles.metricGrid}>
          <SummaryMetric label="今日学习新词" value={fmtInt(todayNew)} />
          <SummaryMetric label="今日复习词" value={fmtInt(todayReview)} />
          <SummaryMetric label="今日学过单词" value={fmtInt(todayWords)} />
          <SummaryMetric label="今日学习时长" value={fmtDuration(numberValue(alltime, ['today_duration_seconds']))} />
          <SummaryMetric label="今日答题正确率" value={fmtPct(todayAccuracy)} />
          <SummaryMetric label="累计学习新词" value={fmtInt(totalLearned)} />
          <SummaryMetric label="累计复习词" value={fmtInt(totalReviewed)} />
          <SummaryMetric label="总学习时长" value={fmtDuration(numberValue(alltime, ['duration_seconds']))} />
          <SummaryMetric label="连续学习天数" value={`${fmtInt(streakDays)} 天`} />
        </View>
      </Card>

      <Card>
        <View style={styles.sectionHead}>
          <Heading>模式占比与各模式统计</Heading>
          <Text style={styles.sectionMeta}>{fmtInt(totalSessions)} 轮</Text>
        </View>
        <ModeChart modeBreakdown={modeBreakdown} pieChart={pieChart} />
      </Card>

      <Card>
        <View style={styles.sectionHead}>
          <Heading>学习记录</Heading>
          <Text style={styles.sectionMeta}>近 7 天</Text>
        </View>
        <DailyChart rows={daily} />
      </Card>

      <Card>
        <View style={styles.sectionHead}>
          <Heading>章节学习分布</Heading>
          <Text style={styles.sectionMeta}>{chapterBreakdown.length} 章</Text>
        </View>
        <ChapterChart rows={chapterBreakdown} />
      </Card>

      <Card>
        <View style={styles.sectionHead}>
          <Heading>艾宾浩斯曲线</Heading>
          <Text style={styles.sectionMeta}>按时率 {fmtPct(numberValue(alltime, ['ebbinghaus_rate']))}</Text>
        </View>
        <EbbinghausChart alltime={alltime} />
      </Card>

      <Card>
        <View style={styles.sectionHead}>
          <Heading>统一学习画像</Heading>
        </View>
        <ProfileRow label="连续学习" value={`${fmtInt(streakDays)} 天`} />
        <ProfileRow label="薄弱模式" value={String(profileSummary.weakest_mode_label ?? profileSummary.weakest_mode ?? '')} />
        <ProfileRow label="主要模式" value={String(profileSummary.dominant_mode_label ?? profileSummary.dominant_mode ?? '')} />
        {focusWords.length ? (
          <View style={styles.wordStrip}>
            {focusWords.map(item => <Text key={String(item.word)} style={styles.wordChip}>{String(item.word)}</Text>)}
          </View>
        ) : null}
        {repeatedTopics.length ? (
          <View style={styles.topicBox}>
            {repeatedTopics.map(item => <Text key={String(item.topic ?? item.name)} style={styles.topicText}>{String(item.topic ?? item.name)}</Text>)}
          </View>
        ) : null}
      </Card>
    </ScreenScroll>
  )
}

const styles = StyleSheet.create({
  chapterFill: {
    backgroundColor: theme.colors.primary,
    borderRadius: theme.radius.pill,
    height: '100%',
  },
  chapterList: {
    gap: theme.spacing.sm,
  },
  chapterName: {
    color: theme.colors.text,
    flex: 1,
    fontSize: theme.typography.caption,
    fontWeight: '900',
  },
  chapterRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: theme.spacing.sm,
  },
  chapterTrack: {
    backgroundColor: theme.colors.surfaceInset,
    borderRadius: theme.radius.pill,
    flex: 1,
    height: 8,
    overflow: 'hidden',
  },
  chapterValue: {
    color: theme.colors.muted,
    fontSize: theme.typography.caption,
    fontWeight: '800',
    width: 36,
  },
  dailyBar: {
    backgroundColor: theme.colors.primary,
    borderRadius: theme.radius.pill,
    bottom: 0,
    position: 'absolute',
    width: '100%',
  },
  dailyBarWrap: {
    backgroundColor: theme.colors.surfaceInset,
    borderRadius: theme.radius.pill,
    flex: 1,
    marginVertical: theme.spacing.xs,
    overflow: 'hidden',
    width: 16,
  },
  dailyChart: {
    flexDirection: 'row',
    gap: theme.spacing.sm,
    height: 140,
    justifyContent: 'space-between',
  },
  dailyColumn: {
    alignItems: 'center',
    flex: 1,
  },
  dailyDate: {
    color: theme.colors.muted,
    fontSize: 10,
    fontWeight: '800',
  },
  dailyValue: {
    color: theme.colors.text,
    fontSize: 11,
    fontWeight: '900',
  },
  legendDot: {
    borderRadius: theme.radius.pill,
    height: 9,
    width: 9,
  },
  legendName: {
    color: theme.colors.text,
    flex: 1,
    fontSize: theme.typography.caption,
    fontWeight: '900',
  },
  legendRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: theme.spacing.sm,
    marginTop: theme.spacing.sm,
  },
  legendValue: {
    color: theme.colors.muted,
    fontSize: theme.typography.caption,
    fontWeight: '800',
  },
  metricCard: {
    backgroundColor: theme.colors.surfaceInset,
    borderColor: theme.colors.border,
    borderRadius: theme.radius.card,
    borderWidth: 1,
    flexBasis: '48%',
    flexGrow: 1,
    minHeight: 92,
    padding: theme.spacing.md,
  },
  metricGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: theme.spacing.sm,
  },
  metricLabel: {
    color: theme.colors.muted,
    fontSize: theme.typography.caption,
    fontWeight: '800',
    lineHeight: 18,
    marginTop: theme.spacing.xs,
  },
  metricValue: {
    color: theme.colors.text,
    fontSize: 19,
    fontWeight: '900',
  },
  profileLabel: {
    color: theme.colors.text,
    fontSize: theme.typography.label,
    fontWeight: '900',
  },
  profileRow: {
    alignItems: 'center',
    borderBottomColor: theme.colors.border,
    borderBottomWidth: 1,
    flexDirection: 'row',
    gap: theme.spacing.md,
    justifyContent: 'space-between',
    paddingVertical: theme.spacing.sm,
  },
  profileValue: {
    color: theme.colors.muted,
    flex: 1,
    fontSize: theme.typography.label,
    fontWeight: '700',
    textAlign: 'right',
  },
  sectionHead: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: theme.spacing.sm,
  },
  sectionMeta: {
    color: theme.colors.muted,
    fontSize: theme.typography.caption,
    fontWeight: '900',
  },
  stackBar: {
    borderRadius: theme.radius.pill,
    flexDirection: 'row',
    height: 16,
    overflow: 'hidden',
  },
  stackSlice: {
    height: '100%',
  },
  stageFill: {
    backgroundColor: theme.colors.success,
    borderRadius: theme.radius.pill,
    height: '100%',
  },
  stageList: {
    gap: theme.spacing.sm,
  },
  stageName: {
    color: theme.colors.text,
    fontSize: theme.typography.caption,
    fontWeight: '900',
    width: 38,
  },
  stageRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: theme.spacing.sm,
  },
  stageTrack: {
    backgroundColor: theme.colors.surfaceInset,
    borderRadius: theme.radius.pill,
    flex: 1,
    height: 9,
    overflow: 'hidden',
  },
  stageValue: {
    color: theme.colors.muted,
    fontSize: theme.typography.caption,
    fontWeight: '800',
    width: 42,
  },
  topicBox: {
    backgroundColor: theme.colors.surfaceInset,
    borderRadius: theme.radius.card,
    gap: theme.spacing.xs,
    marginTop: theme.spacing.md,
    padding: theme.spacing.md,
  },
  topicText: {
    color: theme.colors.muted,
    fontSize: theme.typography.caption,
    lineHeight: 19,
  },
  wordChip: {
    backgroundColor: theme.colors.accentSoft,
    borderRadius: theme.radius.pill,
    color: theme.colors.accentDark,
    fontSize: theme.typography.caption,
    fontWeight: '800',
    paddingHorizontal: theme.spacing.sm,
    paddingVertical: theme.spacing.xs,
  },
  wordStrip: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: theme.spacing.xs,
    marginTop: theme.spacing.md,
  },
})
