import React, { useEffect, useState } from 'react'
import {
  BarChart3,
  BookOpen,
  Bot,
  FileText,
  NotebookPen,
  Search,
  SquarePen,
  TriangleAlert,
  type LucideIcon,
} from 'lucide-react-native'
import { Pressable, StyleSheet, Text, View } from 'react-native'
import type { HomeTodoAction } from '@ielts-vocab/app-core'
import { loadHomeTodos, loadLearningStats } from '../api/learnerApi'
import { Body, Card, Heading, Meta, PrimaryButton, ScreenScroll, StatusText } from '../components/primitives'
import type { Navigate, NavigateOptions, ScreenKey } from '../navigation/types'
import { theme } from '../theme'

type HomeState = {
  learnedWords: number
  totalWords: number
  wrongWords: number
  todos: Array<{
    action: HomeTodoAction
    cta_label: string
    subtitle: string
    target_path: string
    title: string
  }>
}

const quickActions: Array<{
  Icon: LucideIcon
  backgroundColor: string
  color: string
  label: string
  options?: NavigateOptions
  screen: ScreenKey
}> = [
  { Icon: BookOpen, backgroundColor: theme.colors.accentSoft, color: theme.colors.accent, label: '词书', screen: 'books' },
  { Icon: SquarePen, backgroundColor: theme.colors.infoSoft, color: theme.colors.info, label: '练习', screen: 'practice', options: { mode: 'smart' } },
  { Icon: TriangleAlert, backgroundColor: theme.colors.dangerSoft, color: theme.colors.danger, label: '错词', screen: 'errors' },
  { Icon: BarChart3, backgroundColor: theme.colors.emeraldSoft, color: theme.colors.emerald, label: '统计', screen: 'stats' },
  { Icon: FileText, backgroundColor: theme.colors.roseSoft, color: theme.colors.rose, label: '真题', screen: 'exams' },
  { Icon: NotebookPen, backgroundColor: theme.colors.infoSoft, color: theme.colors.info, label: '日志', screen: 'journal' },
  { Icon: Bot, backgroundColor: theme.colors.accentSoft, color: theme.colors.accent, label: 'AI', screen: 'ai' },
  { Icon: Search, backgroundColor: theme.colors.emeraldSoft, color: theme.colors.emerald, label: '查词', screen: 'search' },
]

function readNumber(source: Record<string, unknown>, key: string): number {
  const value = source[key]
  return typeof value === 'number' ? value : 0
}

function normalizeCtaLabel(label: string, action: HomeTodoAction): string {
  const task = action.task || action.kind
  if (task === 'due-review') return '到期复习'
  if (task === 'error-review') return '清理错词'
  if (task === 'speaking') return '跟读练习'
  return label.replace('五维复习', '基础复习').replace('错维回流', '错词强化')
}

function routeTarget(
  path: string,
  action: HomeTodoAction,
): { options?: NavigateOptions; screen: ScreenKey } {
  const task = action.task || action.kind
  const bookId = action.book_id == null ? undefined : String(action.book_id)
  const chapterId = action.chapter_id ?? undefined
  if (task === 'due-review') return { screen: 'practice', options: { mode: 'quickmemory' } }
  if (task === 'error-review') return { screen: 'errors' }
  if (task === 'continue-book') return { screen: 'books', options: { bookId, chapterId } }
  if (task === 'speaking') return { screen: 'practice', options: { mode: 'follow' } }
  if (path.includes('/books')) return { screen: 'books' }
  if (path.includes('/errors')) return { screen: 'errors' }
  if (path.includes('/stats')) return { screen: 'stats' }
  if (path.includes('/journal')) return { screen: 'journal' }
  if (path.includes('/exams')) return { screen: 'exams' }
  return { screen: 'practice' }
}

export function HomeScreen({ navigate }: { navigate: Navigate }) {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [state, setState] = useState<HomeState>({
    learnedWords: 0,
    totalWords: 0,
    wrongWords: 0,
    todos: [],
  })

  useEffect(() => {
    let active = true
    Promise.all([loadLearningStats(), loadHomeTodos()])
      .then(([stats, todos]) => {
        const summary = stats.summary ?? {}
        const alltime = stats.alltime ?? {}
        if (!active) return
        setState({
          learnedWords: readNumber(summary, 'learned_words') || readNumber(alltime, 'learned_words'),
          totalWords: readNumber(summary, 'total_words') || readNumber(alltime, 'total_words'),
          wrongWords: readNumber(summary, 'wrong_words') || readNumber(alltime, 'wrong_words'),
          todos: [...todos.primary_items, ...todos.overflow_items].map(item => ({
            action: item.action,
            title: item.title,
            subtitle: item.subtitle || item.description,
            target_path: item.target_path,
            cta_label: normalizeCtaLabel(item.action.cta_label || item.cta_label || '开始', item.action),
          })),
        })
      })
      .catch(err => {
        if (active) setError(err instanceof Error ? err.message : '学习统计加载失败')
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [])

  const progress = state.totalWords > 0 ? Math.min(100, Math.round((state.learnedWords / state.totalWords) * 100)) : 0

  return (
    <ScreenScroll hideHeader title="雅思冲刺" subtitle="今日优先处理复习、错词和下一组新词。">
      <Pressable onPress={() => navigate('search')} style={styles.searchBar}>
        <Search color={theme.colors.accent} size={22} strokeWidth={2.5} />
        <Text style={styles.searchText}>搜索单词、例句或笔记</Text>
        <Text style={styles.searchAction}>搜索</Text>
      </Pressable>
      <StatusText error={error} loading={loading} />
      <Card style={styles.heroCard}>
        <View style={styles.heroTop}>
          <View>
            <Meta>学习概览</Meta>
            <Heading>{progress ? `已完成 ${progress}%` : '今天从第一组开始'}</Heading>
          </View>
          <View style={styles.badge}>
            <Text style={styles.badgeValue}>{state.wrongWords}</Text>
            <Text style={styles.badgeLabel}>错词</Text>
          </View>
        </View>
        <View style={styles.progressTrack}>
          <View style={[styles.progressFill, { width: `${progress}%` }]} />
        </View>
        <View style={styles.metricRow}>
          <View style={styles.metric}>
            <Text style={styles.metricValue}>{state.learnedWords}</Text>
            <Text style={styles.metricLabel}>已学</Text>
          </View>
          <View style={styles.metric}>
            <Text style={styles.metricValue}>{state.totalWords}</Text>
            <Text style={styles.metricLabel}>总词</Text>
          </View>
          <View style={styles.metric}>
            <Text style={styles.metricValue}>{Math.max(state.totalWords - state.learnedWords, 0)}</Text>
            <Text style={styles.metricLabel}>待攻克</Text>
          </View>
        </View>
      </Card>
      <Card>
        <View style={styles.sectionHeader}>
          <Heading>快捷入口</Heading>
          <PrimaryButton label="到期复习" tone="accent" onPress={() => navigate('practice', { mode: 'quickmemory' })} />
        </View>
        <View style={styles.quickGrid}>
          {quickActions.map(item => (
            <Pressable
              accessibilityRole="button"
              key={item.label}
              onPress={() => navigate(item.screen, item.options)}
              style={styles.quickTile}
            >
              <View style={[styles.quickIcon, { backgroundColor: item.backgroundColor }]}>
                <item.Icon color={item.color} size={24} strokeWidth={2.5} />
              </View>
              <Text style={styles.quickLabel}>{item.label}</Text>
            </Pressable>
          ))}
        </View>
      </Card>
      {state.todos.map((todo, index) => (
        <Card key={`${todo.title}-${index}`}>
          <View style={styles.todoHeader}>
            <Text style={styles.todoIndex}>{String(index + 1).padStart(2, '0')}</Text>
            <Meta>推荐任务</Meta>
          </View>
          <Heading>{todo.title || '学习任务'}</Heading>
          {todo.subtitle ? <Body>{todo.subtitle}</Body> : <Meta>系统推荐的下一步学习动作。</Meta>}
          <PrimaryButton
            label={todo.cta_label}
            tone={index === 0 ? 'primary' : 'neutral'}
            onPress={() => {
              const target = routeTarget(todo.target_path, todo.action)
              navigate(target.screen, target.options)
            }}
          />
        </Card>
      ))}
      {!loading && !state.todos.length ? (
        <Card>
          <Heading>今天很清爽</Heading>
          <Body>可以从词书、错词或真题任选一个入口开始。</Body>
        </Card>
      ) : null}
    </ScreenScroll>
  )
}

const styles = StyleSheet.create({
  badge: {
    alignItems: 'center',
    backgroundColor: theme.colors.dangerSoft,
    borderRadius: theme.radius.card,
    minWidth: 64,
    padding: theme.spacing.sm,
  },
  badgeLabel: {
    color: theme.colors.danger,
    fontSize: theme.typography.caption,
    fontWeight: '700',
  },
  badgeValue: {
    color: theme.colors.danger,
    fontSize: 22,
    fontWeight: '900',
  },
  heroCard: {
    backgroundColor: theme.colors.surfaceElevated,
  },
  heroTop: {
    alignItems: 'flex-start',
    flexDirection: 'row',
    gap: theme.spacing.md,
    justifyContent: 'space-between',
  },
  metric: {
    backgroundColor: theme.colors.surfaceInset,
    borderRadius: theme.radius.card,
    flex: 1,
    padding: theme.spacing.sm,
  },
  metricLabel: {
    color: theme.colors.muted,
    fontSize: theme.typography.caption,
    fontWeight: '700',
    marginTop: theme.spacing.xs,
  },
  metricRow: {
    flexDirection: 'row',
    gap: theme.spacing.sm,
    marginTop: theme.spacing.md,
  },
  metricValue: {
    color: theme.colors.text,
    fontSize: 20,
    fontWeight: '900',
  },
  progressFill: {
    backgroundColor: theme.colors.accent,
    borderRadius: theme.radius.pill,
    height: 8,
  },
  progressTrack: {
    backgroundColor: theme.colors.accentSoft,
    borderRadius: theme.radius.pill,
    height: 8,
    marginTop: theme.spacing.md,
    overflow: 'hidden',
  },
  quickGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: theme.spacing.sm,
  },
  quickIcon: {
    alignItems: 'center',
    borderRadius: theme.radius.card,
    height: 42,
    justifyContent: 'center',
    width: 42,
  },
  quickLabel: {
    color: theme.colors.text,
    fontSize: theme.typography.caption,
    fontWeight: '800',
    marginTop: theme.spacing.xs,
  },
  quickTile: {
    alignItems: 'center',
    flexBasis: '22%',
    flexGrow: 1,
    minHeight: 76,
  },
  searchAction: {
    backgroundColor: theme.colors.accent,
    borderRadius: theme.radius.pill,
    color: theme.colors.textInverse,
    fontSize: theme.typography.label,
    fontWeight: '900',
    paddingHorizontal: theme.spacing.md,
    paddingVertical: theme.spacing.xs,
  },
  searchBar: {
    alignItems: 'center',
    backgroundColor: theme.colors.surfaceElevated,
    borderColor: theme.colors.borderStrong,
    borderRadius: theme.radius.pill,
    borderWidth: 1,
    elevation: 2,
    flexDirection: 'row',
    gap: theme.spacing.sm,
    marginBottom: theme.spacing.md,
    paddingHorizontal: theme.spacing.md,
    paddingVertical: theme.spacing.sm,
    shadowColor: theme.colors.shadow,
    shadowOffset: { height: 6, width: 0 },
    shadowOpacity: 0.05,
    shadowRadius: 12,
  },
  searchText: {
    color: theme.colors.muted,
    flex: 1,
    fontSize: theme.typography.label,
    fontWeight: '700',
  },
  sectionHeader: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: theme.spacing.md,
    justifyContent: 'space-between',
    marginBottom: theme.spacing.sm,
  },
  todoHeader: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: theme.spacing.sm,
    marginBottom: theme.spacing.xs,
  },
  todoIndex: {
    color: theme.colors.primary,
    fontSize: theme.typography.caption,
    fontWeight: '900',
  },
})
