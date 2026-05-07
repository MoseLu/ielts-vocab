import React, { useEffect, useMemo, useState } from 'react'
import { BarChart3, Brain, Clock3, RotateCcw, Target, TriangleAlert, type LucideIcon } from 'lucide-react-native'
import { Pressable, StyleSheet, Text, View } from 'react-native'
import { PRACTICE_MODE_LABELS } from '@ielts-vocab/app-core'
import { loadLearnerProfile, loadLearningStats } from '../api/learnerApi'
import { Card, Heading, Meta, PrimaryButton, ScreenScroll, StatusText } from '../components/primitives'
import type { Navigate } from '../navigation/types'
import { theme } from '../theme'

type AnyRecord = Record<string, unknown>

function numberValue(source: AnyRecord | undefined, keys: string[]): number {
  for (const key of keys) {
    const value = source?.[key]
    if (typeof value === 'number') return value
    if (typeof value === 'string' && value.trim()) return Number(value) || 0
  }
  return 0
}

function arrayValue(source: AnyRecord, key: string): AnyRecord[] {
  const value = source[key]
  return Array.isArray(value) ? value.filter((item): item is AnyRecord => !!item && typeof item === 'object') : []
}

function textArray(source: AnyRecord, key: string): string[] {
  const value = source[key]
  return Array.isArray(value) ? value.map(String).filter(Boolean) : []
}

function pct(value: number): string {
  if (!Number.isFinite(value) || value <= 0) return '0%'
  return `${Math.round(value)}%`
}

function MetricCard({ Icon, label, tone, value }: { Icon: LucideIcon; label: string; tone: string; value: string }) {
  return (
    <View style={styles.metricCard}>
      <View style={[styles.metricIcon, { backgroundColor: tone }]}>
        <Icon color={theme.colors.text} size={18} strokeWidth={2.4} />
      </View>
      <Text style={styles.metricValue}>{value}</Text>
      <Text style={styles.metricLabel}>{label}</Text>
    </View>
  )
}

export function StatsScreen({ navigate }: { navigate: Navigate }) {
  const [summary, setSummary] = useState<AnyRecord>({})
  const [alltime, setAlltime] = useState<AnyRecord>({})
  const [modeBreakdown, setModeBreakdown] = useState<AnyRecord[]>([])
  const [wrongWords, setWrongWords] = useState<AnyRecord>({})
  const [profile, setProfile] = useState<AnyRecord>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([loadLearningStats(), loadLearnerProfile()])
      .then(([nextStats, nextProfile]) => {
        setSummary(nextStats.summary ?? {})
        setAlltime(nextStats.alltime ?? {})
        setModeBreakdown(nextStats.mode_breakdown ?? [])
        setWrongWords(nextStats.wrong_words ?? {})
        setProfile(nextProfile)
      })
      .catch(err => setError(err instanceof Error ? err.message : '统计加载失败'))
      .finally(() => setLoading(false))
  }, [])

  const learned = numberValue(summary, ['learned_words']) || numberValue(alltime, ['learned_words'])
  const total = numberValue(summary, ['total_words']) || numberValue(alltime, ['total_words'])
  const wrong = numberValue(summary, ['wrong_words']) || numberValue(wrongWords, ['active_count', 'total', 'count'])
  const streak = numberValue(summary, ['streak_days', 'current_streak'])
  const progress = total > 0 ? Math.min(100, (learned / total) * 100) : 0
  const focusWords = arrayValue(profile, 'focus_words').slice(0, 4)
  const nextActions = textArray(profile, 'next_actions').slice(0, 3)
  const dimensions = arrayValue(profile, 'dimensions').slice(0, 4)
  const modeMax = useMemo(
    () => Math.max(1, ...modeBreakdown.map(item => numberValue(item, ['words_studied', 'count', 'sessions']))),
    [modeBreakdown],
  )

  return (
    <ScreenScroll hideHeader title="学习统计" subtitle="学习概览、错词趋势、模式表现和画像建议。">
      <StatusText error={error} loading={loading} />
      <Card style={styles.hero}>
        <View style={styles.heroTop}>
          <View style={styles.heroCopy}>
            <Meta>学习总览</Meta>
            <Text style={styles.heroTitle}>{pct(progress)} 完成度</Text>
            <View style={styles.progressTrack}>
              <View style={[styles.progressFill, { width: `${progress}%` }]} />
            </View>
          </View>
          <View style={styles.scoreBubble}>
            <Text style={styles.scoreValue}>{learned}</Text>
            <Text style={styles.scoreLabel}>已学词</Text>
          </View>
        </View>
      </Card>
      <View style={styles.metricGrid}>
        <MetricCard Icon={Target} label="总词库" tone={theme.colors.primarySoft} value={String(total)} />
        <MetricCard Icon={TriangleAlert} label="错词" tone={theme.colors.dangerSoft} value={String(wrong)} />
        <MetricCard Icon={Clock3} label="连续天数" tone={theme.colors.infoSoft} value={String(streak)} />
        <MetricCard Icon={RotateCcw} label="待复习" tone={theme.colors.emeraldSoft} value={String(numberValue(alltime, ['ebbinghaus_due_total']))} />
      </View>
      <Card>
        <View style={styles.sectionHead}>
          <Heading>模式分布</Heading>
          <BarChart3 color={theme.colors.muted} size={20} />
        </View>
        {modeBreakdown.length ? modeBreakdown.slice(0, 6).map((item, index) => {
          const mode = String(item.mode ?? '')
          const value = numberValue(item, ['words_studied', 'count', 'sessions'])
          return (
            <View key={`${mode}-${index}`} style={styles.modeRow}>
              <View style={styles.modeLabelRow}>
                <Text style={styles.modeLabel}>{PRACTICE_MODE_LABELS[mode as keyof typeof PRACTICE_MODE_LABELS] || mode || '练习'}</Text>
                <Text style={styles.modeValue}>{value}</Text>
              </View>
              <View style={styles.modeTrack}>
                <View style={[styles.modeFill, { width: `${Math.max(8, (value / modeMax) * 100)}%` }]} />
              </View>
            </View>
          )
        }) : <Meta>完成练习后会生成模式分布。</Meta>}
      </Card>
      <Card>
        <View style={styles.sectionHead}>
          <Heading>学习者画像</Heading>
          <Brain color={theme.colors.muted} size={20} />
        </View>
        {dimensions.length ? dimensions.map((item, index) => (
          <View key={String(item.name ?? item.dimension ?? index)} style={styles.profileRow}>
            <Text style={styles.profileTitle}>{String(item.label ?? item.name ?? item.dimension ?? '能力维度')}</Text>
            <Text style={styles.profileMeta}>{String(item.level ?? item.status ?? item.summary ?? '持续观察中')}</Text>
          </View>
        )) : <Meta>暂无画像数据，先完成一组练习即可生成。</Meta>}
        {focusWords.length ? (
          <View style={styles.wordStrip}>
            {focusWords.map(item => <Text key={String(item.word)} style={styles.wordChip}>{String(item.word)}</Text>)}
          </View>
        ) : null}
      </Card>
      <Card>
        <Heading>下一步</Heading>
        {nextActions.length ? nextActions.map(action => <Text key={action} style={styles.actionText}>{action}</Text>) : <Meta>今天优先完成到期复习，再处理错词。</Meta>}
        <View style={styles.actionRow}>
          <Pressable style={styles.actionButton} onPress={() => navigate('practice', { mode: 'quickmemory' })}>
            <Text style={styles.actionButtonText}>到期复习</Text>
          </Pressable>
          <Pressable style={[styles.actionButton, styles.secondaryButton]} onPress={() => navigate('errors')}>
            <Text style={styles.secondaryButtonText}>错词本</Text>
          </Pressable>
        </View>
      </Card>
    </ScreenScroll>
  )
}

const styles = StyleSheet.create({
  actionButton: {
    alignItems: 'center',
    backgroundColor: theme.colors.primary,
    borderRadius: theme.radius.control,
    flex: 1,
    minHeight: 46,
    justifyContent: 'center',
  },
  actionButtonText: {
    color: theme.colors.textInverse,
    fontWeight: '800',
  },
  actionRow: {
    flexDirection: 'row',
    gap: theme.spacing.sm,
    marginTop: theme.spacing.md,
  },
  actionText: {
    color: theme.colors.text,
    fontSize: theme.typography.body,
    lineHeight: 24,
    marginTop: theme.spacing.xs,
  },
  hero: {
    backgroundColor: theme.colors.surface,
  },
  heroCopy: {
    flex: 1,
  },
  heroTitle: {
    color: theme.colors.text,
    fontSize: 30,
    fontWeight: '900',
    marginTop: theme.spacing.xs,
  },
  heroTop: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: theme.spacing.md,
  },
  metricCard: {
    backgroundColor: theme.colors.surfaceElevated,
    borderColor: theme.colors.border,
    borderRadius: theme.radius.card,
    borderWidth: 1,
    flexBasis: '48%',
    flexGrow: 1,
    padding: theme.spacing.md,
  },
  metricGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: theme.spacing.sm,
    marginBottom: theme.spacing.md,
  },
  metricIcon: {
    alignItems: 'center',
    borderRadius: theme.radius.pill,
    height: 34,
    justifyContent: 'center',
    width: 34,
  },
  metricLabel: {
    color: theme.colors.muted,
    fontSize: theme.typography.caption,
    fontWeight: '700',
    marginTop: theme.spacing.xs,
  },
  metricValue: {
    color: theme.colors.text,
    fontSize: 23,
    fontWeight: '900',
    marginTop: theme.spacing.sm,
  },
  modeFill: {
    backgroundColor: theme.colors.primary,
    borderRadius: theme.radius.pill,
    height: '100%',
  },
  modeLabel: {
    color: theme.colors.text,
    flex: 1,
    fontSize: theme.typography.label,
    fontWeight: '800',
  },
  modeLabelRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  modeRow: {
    marginTop: theme.spacing.md,
  },
  modeTrack: {
    backgroundColor: theme.colors.surfaceInset,
    borderRadius: theme.radius.pill,
    height: 9,
    marginTop: theme.spacing.xs,
    overflow: 'hidden',
  },
  modeValue: {
    color: theme.colors.muted,
    fontWeight: '800',
  },
  profileMeta: {
    color: theme.colors.muted,
    flex: 1,
    fontSize: theme.typography.caption,
    textAlign: 'right',
  },
  profileRow: {
    alignItems: 'center',
    borderBottomColor: theme.colors.border,
    borderBottomWidth: 1,
    flexDirection: 'row',
    gap: theme.spacing.md,
    paddingVertical: theme.spacing.sm,
  },
  profileTitle: {
    color: theme.colors.text,
    fontSize: theme.typography.label,
    fontWeight: '800',
  },
  progressFill: {
    backgroundColor: theme.colors.primary,
    borderRadius: theme.radius.pill,
    height: '100%',
  },
  progressTrack: {
    backgroundColor: theme.colors.surfaceInset,
    borderRadius: theme.radius.pill,
    height: 10,
    marginTop: theme.spacing.md,
    overflow: 'hidden',
  },
  scoreBubble: {
    alignItems: 'center',
    backgroundColor: theme.colors.primarySoft,
    borderRadius: theme.radius.card,
    minWidth: 88,
    padding: theme.spacing.md,
  },
  scoreLabel: {
    color: theme.colors.primaryDark,
    fontSize: theme.typography.caption,
    fontWeight: '800',
  },
  scoreValue: {
    color: theme.colors.primaryDark,
    fontSize: 24,
    fontWeight: '900',
  },
  secondaryButton: {
    backgroundColor: theme.colors.surfaceInset,
  },
  secondaryButtonText: {
    color: theme.colors.text,
    fontWeight: '800',
  },
  sectionHead: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
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
