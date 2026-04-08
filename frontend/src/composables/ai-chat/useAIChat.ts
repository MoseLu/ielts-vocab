import { useCallback, useState } from 'react'
import type { AIMessage, LearningContext } from '../../types'
import { getWrongWordDimensionModeLabel, normalizeModeText } from '../../constants/practiceModes'
import {
  AIAskResponseSchema,
  AIPronunciationCheckResponseSchema,
  AIReviewPlanResponseSchema,
  AISpeakingSimulationResponseSchema,
  apiFetch,
  safeParse,
} from '../../lib'
import { buildAIChatContext, syncWrongWords } from './context'
import {
  buildPendingPronunciationPayload,
  buildPendingSpeakingPayload,
  parsePronunciationCommand,
  parseSpeakingCommand,
  type PendingPronunciationState,
  type PendingSpeakingState,
} from './commands'
import { resolveStreamStatusMessage, streamAIReply } from './streaming'

interface UseAIChatOptions {
  userId?: string
}

const REVIEW_PLAN_OPTION = '生成四维复习计划'
const START_SPEAKING_OPTION = '开始口语训练'
const CHANGE_SPEAKING_TASK_OPTION = '换一个口语任务'
const ANSWER_SPEAKING_TASK_OPTION = '我来回答这道题'
const CONTINUE_SPEAKING_OPTION = '我再补充一句'
const RETRY_PRONUNCIATION_OPTION = '再练一次这个词'

export function useAIChat(_options: UseAIChatOptions = {}) {
  const [messages, setMessages] = useState<AIMessage[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [isGreeting, setIsGreeting] = useState(false)
  const [greetingDone, setGreetingDone] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isOpen, setIsOpen] = useState(false)
  const [contextLoaded, setContextLoaded] = useState(false)
  const [pendingPronunciation, setPendingPronunciation] = useState<PendingPronunciationState | null>(null)
  const [pendingSpeaking, setPendingSpeaking] = useState<PendingSpeakingState | null>(null)

  const buildContext = useCallback(() => buildAIChatContext(), [])

  const fetchGreeting = useCallback(async () => {
    setIsGreeting(true)
    try {
      const raw = await apiFetch('/api/ai/greet', {
        method: 'POST',
        body: JSON.stringify({ context: buildContext() }),
      })
      const result = safeParse(AIAskResponseSchema, raw)
      const content = result.success
        ? result.data.reply
        : '你好！我是雅思小助手，有什么我可以帮你的吗？'
      const options = result.success ? result.data.options : undefined
      setMessages([{
        id: 'greet',
        role: 'assistant',
        content,
        options: options ?? undefined,
        timestamp: Date.now(),
      }])
    } catch {
      setMessages([{
        id: 'greet',
        role: 'assistant',
        content: '你好！我是雅思小助手 👋\n\n我可以帮你分析学习进度、找出薄弱单词、制定复习计划，或者生成专属词书。有什么我可以帮你的吗？',
        timestamp: Date.now(),
      }])
    } finally {
      setIsGreeting(false)
      setGreetingDone(true)
    }
  }, [buildContext])

  const openPanel = useCallback(async () => {
    setIsOpen(true)
    if (contextLoaded) return
    setContextLoaded(true)
    await syncWrongWords()
    await fetchGreeting()
  }, [contextLoaded, fetchGreeting])

  const closePanel = useCallback(() => setIsOpen(false), [])

  const sendMessage = useCallback(async (text: string) => {
    const userMsg: AIMessage = {
      id: `user_${Date.now()}`,
      role: 'user',
      content: text,
      timestamp: Date.now(),
    }
    setMessages(prev => [...prev, userMsg])
    setIsLoading(true)
    setError(null)
    let streamingAssistantId: string | null = null
    let streamedContent = ''

    const appendAssistantMessage = (content: string, options?: string[]) => {
      setMessages(prev => [...prev, {
        id: `asst_${Date.now()}`,
        role: 'assistant',
        content,
        options: options ?? undefined,
        timestamp: Date.now(),
      }])
    }

    const createStreamingAssistantMessage = () => {
      const id = `asst_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
      setMessages(prev => [...prev, {
        id,
        role: 'assistant',
        content: '',
        isStreaming: true,
        timestamp: Date.now(),
      }])
      return id
    }

    const updateAssistantMessage = (id: string, patch: Partial<AIMessage>) => {
      setMessages(prev => prev.map(message => (
        message.id === id ? { ...message, ...patch } : message
      )))
    }

    const pausePendingFlows = () => {
      setPendingPronunciation(prev => (prev ? { ...prev, awaitingInput: false } : null))
      setPendingSpeaking(prev => (prev ? { ...prev, awaitingResponse: false } : null))
    }

    const startPronunciationFlow = (context: LearningContext) => {
      const currentWord = String(context.currentWord || '').trim()
      const word = pendingPronunciation?.word || currentWord
      if (!word) {
        appendAssistantMessage(
          '先打开一个正在学习的单词，我就能按当前词带你练发音。你也可以先做一轮口语任务。',
          [START_SPEAKING_OPTION, REVIEW_PLAN_OPTION],
        )
        return
      }
      setPendingPronunciation({ word, awaitingInput: true })
      setPendingSpeaking(prev => (prev ? { ...prev, awaitingResponse: false } : null))
      appendAssistantMessage(
        `我们先练 ${word}。直接回复你刚才读出来的英文就行；如果你愿意，也可以直接发一句包含 ${word} 的英文句子，我会一起记入口语证据。`,
        [START_SPEAKING_OPTION, REVIEW_PLAN_OPTION],
      )
    }

    const promptSpeakingReply = () => {
      if (!pendingSpeaking) {
        appendAssistantMessage(
          '先给你一道口语题，再直接回答会更顺畅。',
          [START_SPEAKING_OPTION, REVIEW_PLAN_OPTION],
        )
        return
      }
      const targetWordsText = pendingSpeaking.targetWords.length > 0
        ? `，尽量带上 ${pendingSpeaking.targetWords.join('、')}`
        : ''
      setPendingSpeaking(prev => (prev ? { ...prev, awaitingResponse: true } : null))
      setPendingPronunciation(prev => (prev ? { ...prev, awaitingInput: false } : null))
      appendAssistantMessage(
        `直接回复你的英文回答就行，我会按刚才这道题继续记录口语证据${targetWordsText}。`,
        [CHANGE_SPEAKING_TASK_OPTION, REVIEW_PLAN_OPTION],
      )
    }

    try {
      const normalized = text.trim()
      const context = buildContext() as LearningContext
      const correctionMatch = normalized.match(/^(?:\/correct\s+|帮我纠正这句话[：:]?\s*|纠正这句话[：:]?\s*)([\s\S]+)$/)
      const exampleMatch = normalized.match(/^给我\s+(.+?)\s+的(?:真题)?例句$/)
      const synonymsMatch = normalized.match(/^辨析\s+(.+?)\s+(?:和|vs)\s+(.+)$/i)
      const familyMatch = normalized.match(/^查看\s+(.+?)\s+的词族$/)
      const wantsCollocation = normalized === '开始搭配训练'
      const wantsPlan = /^(生成四维复习计划|生成复习计划|查看复习计划)$/.test(normalized)
      const wantsAssessment = /^(开始词汇量评估|做词汇量评估)$/.test(normalized)

      const pronunciationPayload = parsePronunciationCommand(normalized, context)
      const pronunciationFollowUpPayload = pendingPronunciation?.awaitingInput
        ? buildPendingPronunciationPayload(normalized, pendingPronunciation)
        : null
      const speakingFollowUpPayload = pendingSpeaking?.awaitingResponse
        ? buildPendingSpeakingPayload(normalized, pendingSpeaking)
        : null

      const wantsPronunciationStart = /^(开始发音训练|练这个词的发音|帮我检查发音|检查这个词的发音|我来跟读这个词|再练一次这个词)$/.test(normalized)
      const wantsSpeakingReply = /^(我来回答这道题|我再补充一句)$/.test(normalized)
      const wantsPronunciation = pronunciationPayload !== null
        || pronunciationFollowUpPayload !== null
        || /^\/pronounce\b/i.test(normalized)
        || /^(记录发音|发音记录)/.test(normalized)
      const wantsSpeaking = /^\/speaking\b/i.test(normalized)
        || speakingFollowUpPayload !== null
        || /^(开始口语训练|开始口语任务|给我一个口语任务|来一轮口语训练|换一个口语任务|换个口语题|再来一道口语题|记录口语回答|我的口语回答)/.test(normalized)

      if (wantsPronunciationStart) {
        startPronunciationFlow(context)
        return
      }
      if (wantsSpeakingReply) {
        promptSpeakingReply()
        return
      }
      if (correctionMatch) {
        pausePendingFlows()
        const sentence = correctionMatch[1].trim()
        const result = await apiFetch<Record<string, unknown>>('/api/ai/correct-text', {
          method: 'POST',
          body: JSON.stringify({ text: sentence }),
        })
        const upgrades = Array.isArray(result.upgrades) ? result.upgrades as Array<Record<string, string>> : []
        const collocations = Array.isArray(result.collocations) ? result.collocations as Array<Record<string, string>> : []
        const lines = [
          '写作纠错结果：',
          `- 语法：${result.grammar_ok ? '基本正确' : '建议优化'}`,
          `- 修正句：${String(result.corrected_sentence || sentence)}`,
        ]
        if (upgrades.length) {
          lines.push('- 词汇升级：')
          upgrades.slice(0, 3).forEach(item => lines.push(`  ${item.from} -> ${item.to}（${item.reason || '提升学术表达'}）`))
        }
        if (collocations.length) {
          lines.push('- 搭配建议：')
          collocations.slice(0, 3).forEach(item => lines.push(`  ${item.wrong} -> ${item.right}`))
        }
        lines.push(String(result.encouragement || '继续保持，建议多练 Task 2 学术表达。'))
        appendAssistantMessage(lines.join('\n'))
        return
      }
      if (exampleMatch || normalized.startsWith('/example ')) {
        pausePendingFlows()
        const word = exampleMatch?.[1]?.trim() || normalized.replace('/example ', '').trim()
        const result = await apiFetch<{ examples: Array<{ sentence: string; source?: string }> }>(
          `/api/ai/ielts-example?word=${encodeURIComponent(word)}`,
        )
        const lines = ['真题语境例句：', ...result.examples.slice(0, 3).map((item, index) => `${index + 1}. ${item.sentence} (${item.source || 'unknown'})`)]
        appendAssistantMessage(lines.join('\n'))
        return
      }
      if (synonymsMatch || normalized.startsWith('/synonyms ')) {
        pausePendingFlows()
        const pair = synonymsMatch
          ? [synonymsMatch[1].trim(), synonymsMatch[2].trim()]
          : normalized.replace('/synonyms ', '').split(/\s+vs\s+|\s+/i)
        const [a, b] = pair
        const result = await apiFetch<{ summary: string; quiz?: { question?: string } }>('/api/ai/synonyms-diff', {
          method: 'POST',
          body: JSON.stringify({ a, b }),
        })
        appendAssistantMessage(`${result.summary}\n${result.quiz?.question || ''}`.trim())
        return
      }
      if (familyMatch || normalized.startsWith('/family ')) {
        pausePendingFlows()
        const word = familyMatch?.[1]?.trim() || normalized.replace('/family ', '').trim()
        const result = await apiFetch<Record<string, unknown>>(`/api/ai/word-family?word=${encodeURIComponent(word)}`)
        const variants = (result.variants as Array<Record<string, string>> | undefined) || []
        appendAssistantMessage(
          variants.length
            ? `词族树 ${word}：\n${variants.map(item => `- ${item.word} (${item.pos})`).join('\n')}`
            : String(result.message || '暂无词族数据'),
        )
        return
      }
      if (wantsCollocation || normalized.startsWith('/collocation')) {
        pausePendingFlows()
        const result = await apiFetch<{ items: Array<{ wrong: string; right: string; explanation: string }> }>('/api/ai/collocations/practice?count=5')
        appendAssistantMessage(`搭配训练：\n${result.items.map(item => `- ${item.wrong} -> ${item.right}（${item.explanation}）`).join('\n')}`)
        return
      }
      if (wantsPronunciation) {
        const payload = pronunciationPayload ?? pronunciationFollowUpPayload
        if (!payload) {
          startPronunciationFlow(context)
          return
        }

        const raw = await apiFetch('/api/ai/pronunciation-check', {
          method: 'POST',
          body: JSON.stringify({
            ...payload,
            bookId: context.currentBook,
            chapterId: context.currentChapter,
          }),
        })
        const result = safeParse(AIPronunciationCheckResponseSchema, raw)
        if (!result.success) throw new Error('发音检查响应格式错误')

        setPendingPronunciation({ word: result.data.word, awaitingInput: false })
        setPendingSpeaking(prev => (prev ? { ...prev, awaitingResponse: false } : null))

        const lines = [
          `发音检查：${result.data.word}`,
          `- 分数：${Math.round(result.data.score)}`,
          `- 结果：${result.data.passed ? '通过' : '待强化'}`,
          `- 重音：${result.data.stress_feedback}`,
          `- 元音：${result.data.vowel_feedback}`,
          `- 节奏：${result.data.speed_feedback}`,
          payload.sentence ? '- 已记录：发音 + 造句证据' : '- 已记录：发音证据；再补一句英文句子就能补全口语输出证据。',
        ]
        appendAssistantMessage(lines.join('\n'), [
          RETRY_PRONUNCIATION_OPTION,
          START_SPEAKING_OPTION,
          REVIEW_PLAN_OPTION,
        ])
        return
      }
      if (wantsPlan || normalized.startsWith('/plan')) {
        pausePendingFlows()
        const raw = await apiFetch('/api/ai/review-plan')
        const result = safeParse(AIReviewPlanResponseSchema, raw)
        if (!result.success) throw new Error('复习计划响应格式错误')

        const lines = [`今日复习计划（${result.data.level}）：`]
        if (result.data.mastery_rule) lines.push(normalizeModeText(result.data.mastery_rule))
        if (result.data.priority_dimension) {
          const reason = result.data.priority_reason ? `，原因：${result.data.priority_reason}` : ''
          const priorityLabel = getWrongWordDimensionModeLabel(result.data.priority_dimension, result.data.priority_dimension)
          lines.push(`当前优先维度：${priorityLabel || result.data.priority_dimension}${reason}`)
        }
        if (result.data.dimensions.length > 0) {
          lines.push('四维安排：')
          result.data.dimensions.forEach(item => {
            const schedule = item.schedule_label ? `，周期 ${item.schedule_label}` : ''
            const label = getWrongWordDimensionModeLabel(item.key, item.label) || item.label || '维度'
            lines.push(`- ${label}：${normalizeModeText(item.status_label || '待安排')}${schedule}`)
          })
        }
        if (result.data.plan.length > 0) {
          lines.push('建议动作：')
          lines.push(...result.data.plan.map(item => `- ${normalizeModeText(item)}`))
        }
        appendAssistantMessage(lines.join('\n'))
        return
      }
      if (wantsAssessment || normalized.startsWith('/assessment')) {
        pausePendingFlows()
        const result = await apiFetch<{ questions: Array<{ word: string; definition: string }> }>('/api/ai/vocab-assessment?count=10')
        const preview = result.questions.slice(0, 5).map((item, index) => `${index + 1}. ${item.word}: ${item.definition}`).join('\n')
        appendAssistantMessage(`词汇量评估（预览）：\n${preview}`)
        return
      }
      if (wantsSpeaking) {
        const payload = speakingFollowUpPayload ?? parseSpeakingCommand(normalized, context)
        const raw = await apiFetch('/api/ai/speaking-simulate', {
          method: 'POST',
          body: JSON.stringify({
            part: payload.part,
            topic: payload.topic,
            targetWords: payload.targetWords,
            responseText: payload.responseText,
            bookId: context.currentBook,
            chapterId: context.currentChapter,
          }),
        })
        const result = safeParse(AISpeakingSimulationResponseSchema, raw)
        if (!result.success) throw new Error('口语任务响应格式错误')

        setPendingPronunciation(prev => (prev ? { ...prev, awaitingInput: false } : null))
        setPendingSpeaking({
          part: result.data.part,
          topic: result.data.topic,
          targetWords: payload.targetWords,
          awaitingResponse: !payload.responseText,
        })

        const lines = [
          `口语任务（Part ${result.data.part} / ${result.data.topic}）：`,
          result.data.question,
        ]
        if (payload.targetWords.length > 0) lines.push(`目标词：${payload.targetWords.join('、')}`)
        lines.push(payload.responseText
          ? '已记录你的回答，口语维度会按 1/3/7/15/30 天节点继续安排复现。'
          : '直接回复你的英文回答就行，我会按这道题继续记录口语证据。')
        if (result.data.follow_ups.length > 0) {
          lines.push('追问方向：')
          lines.push(...result.data.follow_ups.map(item => `- ${item}`))
        }
        appendAssistantMessage(
          lines.join('\n'),
          payload.responseText
            ? [CONTINUE_SPEAKING_OPTION, CHANGE_SPEAKING_TASK_OPTION, REVIEW_PLAN_OPTION]
            : [ANSWER_SPEAKING_TASK_OPTION, CHANGE_SPEAKING_TASK_OPTION, REVIEW_PLAN_OPTION],
        )
        return
      }

      pausePendingFlows()
      streamingAssistantId = createStreamingAssistantMessage()
      let streamedOptions: string[] | undefined

      await streamAIReply({
        message: text,
        context,
        onEvent: (event) => {
          if (!streamingAssistantId) return

          if (event.type === 'status') {
            if (!streamedContent.trim()) {
              updateAssistantMessage(streamingAssistantId, {
                content: resolveStreamStatusMessage(event),
                isStreaming: true,
              })
            }
            return
          }
          if (event.type === 'text') {
            streamedContent += event.delta
            updateAssistantMessage(streamingAssistantId, {
              content: streamedContent,
              isStreaming: true,
            })
            return
          }
          if (event.type === 'options') {
            streamedOptions = event.options
            updateAssistantMessage(streamingAssistantId, {
              options: event.options,
              isStreaming: true,
            })
            return
          }
          if (event.type === 'done') {
            streamedContent = event.reply
            streamedOptions = event.options ?? streamedOptions
            updateAssistantMessage(streamingAssistantId, {
              content: event.reply,
              options: streamedOptions,
              isStreaming: false,
            })
            return
          }
          if (event.type === 'error') {
            throw new Error(event.error || 'AI 服务暂时不可用，请稍后重试')
          }
        },
      })
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : '未知错误'
      setError(message)
      if (streamingAssistantId) {
        if (streamedContent.trim()) {
          setMessages(prev => prev.map(messageItem => (
            messageItem.id === streamingAssistantId
              ? { ...messageItem, content: streamedContent, isStreaming: false }
              : messageItem
          )))
        } else {
          setMessages(prev => prev.filter(messageItem => messageItem.id !== streamingAssistantId))
        }
      }
      setMessages(prev => [...prev, {
        id: `err_${Date.now()}`,
        role: 'assistant',
        content: `出错了：${message}`,
        timestamp: Date.now(),
      }])
    } finally {
      setIsLoading(false)
    }
  }, [buildContext, pendingPronunciation, pendingSpeaking])

  return {
    messages,
    isLoading,
    isGreeting,
    greetingDone,
    error,
    isOpen,
    contextLoaded,
    openPanel,
    closePanel,
    sendMessage,
  }
}
