import React, { useEffect, useMemo, useState } from 'react'
import { BarChart3, Brain, ChevronRight, Clock3, Layers3, Sparkles, type LucideIcon } from 'lucide-react-native'
import { Pressable, Text, View } from 'react-native'
import { PRACTICE_MODE_LABELS } from '@ielts-vocab/app-core'
import { loadLearnerProfile, loadLearningStats } from '../api/learnerApi'
import { Card, Heading, Meta, ScreenScroll, StatusText } from '../components/primitives'
import type { Navigate, NavigateOptions } from '../navigation/types'
import { theme } from '../theme'
import { styles } from './StatsScreen.styles'

type AnyRecord = Record<string, unknown>
type StatsSection = NonNullable<NavigateOptions['statsSection']>
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
      <View style={styles.metricGlow} />
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
        {rows.map((item, index) => (
          <View
            key={`${String(item.mode)}-${index}`}
            style={[styles.stackSlice, { backgroundColor: chartColors[index % chartColors.length], flex: Math.max(1, numberValue(item, ['value', 'words_studied', 'attempts', 'sessions'])) }]}
          />
        ))}
      </View>
      {modeBreakdown.slice(0, 7).map((item, index) => (
        <View key={`${String(item.mode)}-legend-${index}`} style={styles.legendRow}>
          <View style={[styles.legendDot, { backgroundColor: chartColors[index % chartColors.length] }]} />
          <Text style={styles.legendName}>{labelForMode(item.mode)}</Text>
          <Text style={styles.legendValue}>{fmtInt(numberValue(item, ['words_studied', 'value']))} 词 · {fmtPct(numberValue(item, ['accuracy']))}</Text>
        </View>
      ))}
    </>
  )
}

function ChapterChart({ rows }: { rows: AnyRecord[] }) {
  const data = rows.slice(0, 8)
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
            <View style={styles.chapterTrack}><View style={[styles.chapterFill, { width: `${Math.max(5, (words / maxWords) * 100)}%` }]} /></View>
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
            <View style={styles.stageTrack}><View style={[styles.stageFill, { width: `${Math.max(4, Math.min(100, value))}%` }]} /></View>
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

function DetailEntry({ Icon, label, meta, onPress }: { Icon: LucideIcon; label: string; meta: string; onPress: () => void }) {
  return (
    <Pressable accessibilityLabel={`统计详情-${label}`} accessibilityRole="button" onPress={onPress} style={styles.detailEntry} testID={`stats.detail.${label}`}>
      <View style={styles.detailIcon}><Icon color={theme.colors.primaryDark} size={19} strokeWidth={2.4} /></View>
      <View style={styles.detailCopy}>
        <Text style={styles.detailLabel}>{label}</Text>
        <Text numberOfLines={1} style={styles.detailMeta}>{meta}</Text>
      </View>
      <ChevronRight color={theme.colors.textTertiary} size={18} strokeWidth={2.2} />
    </Pressable>
  )
}

function useStatsData() {
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
  const modeBreakdown = arrayValue(stats, 'mode_breakdown')
  const profileSummary = recordValue(profile, 'summary')
  const todayNew = numberValue(alltime, ['today_new_words'])
  const todayReview = numberValue(alltime, ['today_review_words'])
  return {
    alltime,
    chapterBreakdown: arrayValue(stats, 'chapter_breakdown'),
    daily: arrayValue(stats, 'daily'),
    error,
    focusWords: arrayValue(profile, 'focus_words').slice(0, 8),
    loading,
    modeBreakdown,
    pieChart: arrayValue(stats, 'pie_chart'),
    profileSummary,
    repeatedTopics: arrayValue(profile, 'repeated_topics').slice(0, 4),
    streakDays: numberValue(profileSummary, ['streak_days']) || numberValue(alltime, ['streak_days']),
    todayAccuracy: numberValue(alltime, ['today_accuracy']) || numberValue(profileSummary, ['today_accuracy']),
    todayNew,
    todayReview,
    todayWords: numberValue(alltime, ['today_words', 'today_total_words']) || todayNew + todayReview,
    totalLearned: numberValue(alltime, ['total_words', 'learned_words']) || numberValue(summary, ['learned_words']),
    totalReviewed: numberValue(alltime, ['alltime_review_words', 'total_review_words']),
    totalSessions: useMemo(() => modeBreakdown.reduce((sum, item) => sum + numberValue(item, ['sessions']), 0) || numberValue(summary, ['total_sessions']), [modeBreakdown, summary]),
  }
}

export function StatsScreen({ navigate }: { navigate: Navigate }) {
  const data = useStatsData()
  const details: Array<{ Icon: LucideIcon; key: StatsSection; label: string; meta: string }> = [
    { Icon: BarChart3, key: 'modes', label: '练习模式', meta: `${fmtInt(data.totalSessions)} 轮练习的分布与正确率` },
    { Icon: Clock3, key: 'history', label: '学习记录', meta: '查看近 7 天学习节奏' },
    { Icon: Layers3, key: 'chapters', label: '章节分布', meta: `${data.chapterBreakdown.length} 个章节的学习进度` },
    { Icon: Brain, key: 'ebbinghaus', label: '记忆曲线', meta: `按时复习率 ${fmtPct(numberValue(data.alltime, ['ebbinghaus_rate']))}` },
    { Icon: Sparkles, key: 'profile', label: '学习画像', meta: '薄弱模式、重点词和重复主题' },
  ]
  return (
    <ScreenScroll hideHeader title="学习统计">
      <StatusText error={data.error} loading={data.loading} />
      <Card style={styles.heroCard}>
        <Meta>今日摘要</Meta>
        <Heading>先看最需要的四个数字</Heading>
        <View style={styles.metricGrid}>
          <SummaryMetric label="今日学过" value={`${fmtInt(data.todayWords)} 词`} />
          <SummaryMetric label="今日用时" value={fmtDuration(numberValue(data.alltime, ['today_duration_seconds']))} />
          <SummaryMetric label="正确率" value={fmtPct(data.todayAccuracy)} />
          <SummaryMetric label="连续学习" value={`${fmtInt(data.streakDays)} 天`} />
        </View>
        <Text style={styles.heroMeta}>累计新词 {fmtInt(data.totalLearned)} · 累计复习 {fmtInt(data.totalReviewed)}</Text>
      </Card>
      <Card style={styles.detailCard}>
        <Heading>深入查看</Heading>
        <Meta>把图表放到二级页面，首页只保留轻量入口。</Meta>
        <View style={styles.detailList}>
          {details.map(item => <DetailEntry {...item} key={item.key} onPress={() => navigate('statsDetail', { statsSection: item.key })} />)}
        </View>
      </Card>
    </ScreenScroll>
  )
}

export function StatsDetailScreen({ options }: { options?: NavigateOptions }) {
  const data = useStatsData()
  const section = options?.statsSection ?? 'modes'
  const titles: Record<StatsSection, string> = {
    chapters: '章节学习分布',
    ebbinghaus: '艾宾浩斯曲线',
    history: '近 7 天学习记录',
    modes: '模式占比与统计',
    profile: '统一学习画像',
  }
  return (
    <ScreenScroll hideHeader title={titles[section]}>
      <StatusText error={data.error} loading={data.loading} />
      <Card>
        <View style={styles.sectionHead}>
          <Heading>{titles[section]}</Heading>
          {section === 'modes' ? <Text style={styles.sectionMeta}>{fmtInt(data.totalSessions)} 轮</Text> : null}
          {section === 'chapters' ? <Text style={styles.sectionMeta}>{data.chapterBreakdown.length} 章</Text> : null}
          {section === 'ebbinghaus' ? <Text style={styles.sectionMeta}>按时率 {fmtPct(numberValue(data.alltime, ['ebbinghaus_rate']))}</Text> : null}
        </View>
        {section === 'modes' ? <ModeChart modeBreakdown={data.modeBreakdown} pieChart={data.pieChart} /> : null}
        {section === 'history' ? <DailyChart rows={data.daily} /> : null}
        {section === 'chapters' ? <ChapterChart rows={data.chapterBreakdown} /> : null}
        {section === 'ebbinghaus' ? <EbbinghausChart alltime={data.alltime} /> : null}
        {section === 'profile' ? (
          <>
            <ProfileRow label="连续学习" value={`${fmtInt(data.streakDays)} 天`} />
            <ProfileRow label="薄弱模式" value={String(data.profileSummary.weakest_mode_label ?? data.profileSummary.weakest_mode ?? '')} />
            <ProfileRow label="主要模式" value={String(data.profileSummary.dominant_mode_label ?? data.profileSummary.dominant_mode ?? '')} />
            {data.focusWords.length ? <View style={styles.wordStrip}>{data.focusWords.map(item => <Text key={String(item.word)} style={styles.wordChip}>{String(item.word)}</Text>)}</View> : null}
            {data.repeatedTopics.length ? <View style={styles.topicBox}>{data.repeatedTopics.map(item => <Text key={String(item.topic ?? item.name)} style={styles.topicText}>{String(item.topic ?? item.name)}</Text>)}</View> : null}
          </>
        ) : null}
      </Card>
    </ScreenScroll>
  )
}
