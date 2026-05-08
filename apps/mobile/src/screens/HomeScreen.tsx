import React, { useEffect, useState } from 'react'
import {
  BarChart3,
  BookOpen,
  Bot,
  FileText,
  RefreshCcw,
  Search,
  SquarePen,
  Target,
  TriangleAlert,
} from 'lucide-react-native'
import type { HomeTodoAction } from '@ielts-vocab/app-core'
import { loadHomeTodos, loadLearningStats } from '../api/learnerApi'
import {
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

function buildRoomObjects(state: HomeState): StudyRoomObject[] {
  const remainingWords = Math.max(state.totalWords - state.learnedWords, 0)
  const reviewCount = Math.max(Math.round(remainingWords * 0.08), state.todos.length ? 12 : 0)
  return [
    {
      Icon: BookOpen,
      ctaLabel: '打开词书',
      hint: '书架上的词卡会继续沿用当前词书、章节和学习进度。',
      key: 'word-cards',
      label: '词卡',
      screen: 'books',
      tone: 'green',
      value: remainingWords ? `${Math.min(20, remainingWords)} 个新词` : '轻量复盘',
    },
    {
      Icon: RefreshCcw,
      ctaLabel: '开始复习',
      hint: '像点唱机一样先播放今天该复习的词，把记忆重新转起来。',
      key: 'review-player',
      label: '复习',
      options: { mode: 'quickmemory' },
      screen: 'practice',
      tone: 'orange',
      value: `${reviewCount} 词`,
    },
    {
      Icon: SquarePen,
      ctaLabel: '去练习台',
      hint: '基础训练、听力、拼写和释义练习都从这里进入。',
      key: 'practice-desk',
      label: '练习',
      options: { mode: 'smart' },
      screen: 'practice',
      tone: 'blue',
      value: '智能出题',
    },
    {
      Icon: TriangleAlert,
      ctaLabel: '安抚错词',
      hint: '错词急救箱会优先清理最近反复出错的词。',
      key: 'wrong-kit',
      label: '错词',
      screen: 'errors',
      tone: 'red',
      value: `${state.wrongWords} 词`,
    },
    {
      Icon: BarChart3,
      ctaLabel: '查看数据',
      hint: '剪贴板会展示体感更轻的学习数据与复习曲线。',
      key: 'data-board',
      label: '数据',
      screen: 'stats',
      tone: 'green',
      value: `${state.learnedWords}/${state.totalWords}`,
    },
    {
      Icon: Search,
      ctaLabel: '全局查词',
      hint: '百宝箱式入口，适合临时查词、例句和笔记。',
      key: 'treasure-box',
      label: '百宝箱',
      screen: 'search',
      tone: 'orange',
      value: '查词/例句',
    },
    {
      Icon: FileText,
      ctaLabel: '看真题',
      hint: '挑战赛入口保留活动感，但路由到真题和专项练习。',
      key: 'challenge',
      label: '挑战赛',
      screen: 'exams',
      tone: 'pink',
      value: '真题专项',
    },
    {
      Icon: Bot,
      ctaLabel: '问 AI',
      hint: '挂信入口会给出弱项建议、例句和下一步练习策略。',
      key: 'ai-letter',
      label: 'AI 信件',
      screen: 'ai',
      tone: 'purple',
      value: '3 条建议',
    },
    {
      Icon: Target,
      ctaLabel: '开始计划',
      hint: '第一版只做计划展示和入口，不新增真实支付合同。',
      key: 'pro-plan',
      label: '冲刺计划',
      options: { mode: 'smart' },
      screen: 'practice',
      tone: 'pink',
      value: `IELTS ${planPreview.targetScore}`,
    },
  ]
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
  const remainingWords = Math.max(state.totalWords - state.learnedWords, 0)
  const roomObjects = buildRoomObjects(state)
  const todos: StudyRoomTodo[] = state.todos.map(todo => ({
    ctaLabel: todo.cta_label,
    subtitle: todo.subtitle,
    title: todo.title,
  }))

  return (
    <ScreenScroll hideHeader title="雅思冲刺" subtitle="把今日学习入口藏进一间猫咪 IELTS 自习室。">
      <StatusText error={error} loading={loading} />
      <StudyRoomScene
        learnedWords={state.learnedWords}
        onNavigate={navigate}
        onTodoPress={index => {
          const todo = state.todos[index]
          if (!todo) return
          const target = routeTarget(todo.target_path, todo.action)
          navigate(target.screen, target.options)
        }}
        plan={planPreview}
        progress={progress}
        remainingWords={remainingWords}
        roomObjects={roomObjects}
        todos={todos}
        totalWords={state.totalWords}
        wrongWords={state.wrongWords}
      />
    </ScreenScroll>
  )
}
