import React, { useEffect, useState } from 'react'
import type { HomeTodoAction } from '@ielts-vocab/app-core'
import { StyleSheet, View } from 'react-native'
import { loadHomeTodos, loadLearningStats } from '../api/learnerApi'
import {
  StudyPlanPanel,
  StudyRoomScene,
  type StudyRoomObject,
  type StudyRoomTodo,
} from '../components/StudyRoomScene'
import { ScreenScroll, StatusText } from '../components/primitives'
import type { Navigate, NavigateOptions, ScreenKey } from '../navigation/types'

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

type PlanPreviewCard = {
  examDateLabel: string
  targetScore: string
  weakAreas: string[]
}

const planPreview: PlanPreviewCard = {
  examDateLabel: '32 天后',
  targetScore: '7.0',
  weakAreas: ['听力同义替换', '错词召回', '口语跟读'],
}

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

function buildRoomObjects(state: HomeState): { heroAction: StudyRoomObject; sideEntries: StudyRoomObject[] } {
  const remainingWords = Math.max(state.totalWords - state.learnedWords, 0)
  const firstTodo = state.todos[0]
  const nextTarget = firstTodo
    ? routeTarget(firstTodo.target_path, firstTodo.action)
    : { screen: 'practice' as const, options: { mode: 'smart' as const } }
  const todoCount = state.todos.length

  return {
    heroAction: {
      ctaLabel: '继续学习',
      hint: firstTodo?.subtitle || (remainingWords ? `还剩 ${remainingWords} 个词，先完成一组轻量练习。` : '今天从一组智能练习热身。'),
      key: 'continue-study',
      label: firstTodo?.title || '今天继续学习',
      options: nextTarget.options,
      screen: nextTarget.screen,
      tone: 'green',
      value: firstTodo ? firstTodo.cta_label : '智能练习',
    },
    sideEntries: [
      {
        ctaLabel: '进入练习场',
        hint: '基础训练、复习、听写和跟读都从练习场开始。',
        key: 'practice-yard',
        label: '练习场',
        options: { mode: 'smart' },
        screen: 'practice',
        tone: 'blue',
        value: '智能训练',
      },
      {
        ctaLabel: '清理错词',
        hint: '集中处理最近反复出错的词。',
        key: 'wrong-kit',
        label: '错词',
        screen: 'errors',
        tone: 'red',
        value: `${state.wrongWords} 词`,
      },
      {
        ctaLabel: '查看待办',
        hint: '查看今日推荐、学习进度和冲刺弱项。',
        key: 'todo-list',
        label: '待办',
        screen: 'homePlan',
        tone: 'orange',
        value: todoCount ? `${todoCount} 项` : `IELTS ${planPreview.targetScore}`,
      },
    ],
  }
}

function useHomeState() {
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

  return { error, loading, state }
}

function todoCards(state: HomeState): StudyRoomTodo[] {
  return state.todos.map(todo => ({
    ctaLabel: todo.cta_label,
    subtitle: todo.subtitle,
    title: todo.title,
  }))
}

export function HomeScreen({ navigate }: { navigate: Navigate }) {
  const { error, loading, state } = useHomeState()
  const { heroAction, sideEntries } = buildRoomObjects(state)

  return (
    <View style={styles.homeScreen}>
      {error || loading ? (
        <View pointerEvents="none" style={styles.homeStatusOverlay}>
          <StatusText error={error} loading={loading} />
        </View>
      ) : null}
      <StudyRoomScene
        heroAction={heroAction}
        onNavigate={navigate}
        sideEntries={sideEntries}
        wrongWords={state.wrongWords}
      />
    </View>
  )
}

export function HomePlanScreen({ navigate }: { navigate: Navigate }) {
  const { error, loading, state } = useHomeState()
  const progress = state.totalWords > 0 ? Math.min(100, Math.round((state.learnedWords / state.totalWords) * 100)) : 0
  const remainingWords = Math.max(state.totalWords - state.learnedWords, 0)

  return (
    <ScreenScroll hideHeader title="今日计划">
      <StatusText error={error} loading={loading} />
      <StudyPlanPanel
        learnedWords={state.learnedWords}
        onStart={() => navigate('practice', { mode: 'smart' })}
        onTodoPress={index => {
          const todo = state.todos[index]
          if (!todo) return
          const target = routeTarget(todo.target_path, todo.action)
          navigate(target.screen, target.options)
        }}
        plan={planPreview}
        progress={progress}
        remainingWords={remainingWords}
        todos={todoCards(state)}
        totalWords={state.totalWords}
      />
    </ScreenScroll>
  )
}

const styles = StyleSheet.create({
  homeScreen: {
    backgroundColor: '#FFF2E4',
    flex: 1,
  },
  homeStatusOverlay: {
    left: 18,
    position: 'absolute',
    right: 18,
    top: 74,
    zIndex: 20,
  },
})
