import { useState, useCallback, useRef } from 'react'
import { setGlobalLearningContext, getGlobalLearningContext } from '../contexts/AIChatContext'
import type { AIMessage, LearningContext } from '../types'
import { safeParse, AIMessageSchema, AIAskResponseSchema, GeneratedBookSchema } from '../lib'

interface UseAIChatOptions {
  userId?: string
}

export interface GeneratedBook {
  bookId: string
  title: string
  description: string
  chapters: Array<{ id: string; title: string; wordCount: number }>
  words: Array<{
    chapterId: string
    word: string
    phonetic: string
    pos: string
    definition: string
  }>
}

export function useAIChat(_options: UseAIChatOptions = {}) {
  const [messages, setMessages] = useState<AIMessage[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isOpen, setIsOpen] = useState(false)
  const [contextLoaded, setContextLoaded] = useState(false)
  const [learningContext, setLearningContextState] = useState<LearningContext>({})

  const contextRef = useRef<LearningContext>({})
  const setLearningContext = useCallback((ctx: LearningContext) => {
    setLearningContextState(ctx)
    contextRef.current = ctx
  }, [])

  const _syncWrongWords = useCallback(async () => {
    try {
      const token = localStorage.getItem('auth_token')
      const wrongWords = JSON.parse(localStorage.getItem('wrong_words') || '[]')
      if (wrongWords.length > 0 && token) {
        await fetch('/api/ai/wrong-words/sync', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({ words: wrongWords })
        })
      }
    } catch {
      // Non-critical
    }
  }, [])

  const openPanel = useCallback(async () => {
    setIsOpen(true)
    if (contextLoaded) return
    await _syncWrongWords()
    setContextLoaded(true)
    setMessages([{
      id: 'welcome',
      role: 'assistant',
      content: '你好！我是雅思小助手 👋\n\n我可以帮你分析学习进度、制定学习计划，或者为你生成专属复习词书。有什么我可以帮你的吗？',
      timestamp: Date.now()
    }])
  }, [contextLoaded, _syncWrongWords])

  const closePanel = useCallback(() => setIsOpen(false), [])

  const sendMessage = useCallback(async (text: string) => {
    const userMsg: AIMessage = {
      id: `user_${Date.now()}`,
      role: 'user',
      content: text,
      timestamp: Date.now()
    }
    setMessages(prev => [...prev, userMsg])
    setIsLoading(true)
    setError(null)

    try {
      const token = localStorage.getItem('auth_token')
      const resp = await fetch('/api/ai/ask', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          message: text,
          context: { ...contextRef.current, ...getGlobalLearningContext() }
        })
      })

      if (!resp.ok) {
        const err = await resp.json()
        throw new Error(err.error || '请求失败')
      }

      const raw = await resp.json()

      // Validate API response with Zod
      const result = safeParse(AIAskResponseSchema, raw)
      if (!result.success) {
        throw new Error('AI响应格式错误')
      }

      const assistantMsg: AIMessage = {
        id: `asst_${Date.now()}`,
        role: 'assistant',
        content: result.data.reply,
        options: result.data.options || undefined,
        timestamp: Date.now()
      }
      setMessages(prev => [...prev, assistantMsg])
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : '未知错误'
      setError(msg)
      setMessages(prev => [...prev, {
        id: `err_${Date.now()}`,
        role: 'assistant',
        content: `出错了：${msg}`,
        timestamp: Date.now()
      }])
    } finally {
      setIsLoading(false)
    }
  }, [])

  return {
    messages,
    isLoading,
    error,
    isOpen,
    contextLoaded,
    learningContext,
    setLearningContext,
    openPanel,
    closePanel,
    sendMessage,
  }
}
