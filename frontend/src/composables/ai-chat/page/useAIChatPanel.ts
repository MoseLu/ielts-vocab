import { useCallback, useEffect, useRef, useState } from 'react'
import { useAIChat } from '../../../hooks/useAIChat'
import { useSpeechRecognition } from '../../../hooks/useSpeechRecognition'

export const QUICK_ACTIONS: Array<{ label: string; value: string; autoSend: boolean }> = [
  { label: '分析我的学习数据', value: '分析我的学习数据', autoSend: true },
  { label: '写作纠错', value: '帮我纠正这句话：education is very important', autoSend: true },
  { label: '真题例句', value: '给我 significant 的真题例句', autoSend: true },
  { label: '近义词辨析', value: '辨析 affect 和 effect', autoSend: true },
  { label: '词族树', value: '查看 establish 的词族', autoSend: true },
  { label: '搭配训练', value: '开始搭配训练', autoSend: true },
  { label: '四维计划', value: '生成四维复习计划', autoSend: true },
  { label: '词汇评估', value: '开始词汇量评估', autoSend: true },
  { label: '口语任务', value: '开始口语训练', autoSend: true },
  { label: '发音训练', value: '开始发音训练', autoSend: true },
]

export const AI_INPUT_PLACEHOLDER = '输入问题，或发送学习指令'
const AI_INPUT_MAX_HEIGHT = 120

function resizeComposer(textarea: HTMLTextAreaElement | null) {
  if (!textarea) return
  textarea.style.height = 'auto'
  textarea.style.height = `${Math.min(textarea.scrollHeight, AI_INPUT_MAX_HEIGHT)}px`
}

export function useAIChatPanel() {
  const {
    messages,
    isLoading,
    isGreeting,
    greetingDone,
    isOpen,
    contextLoaded,
    openPanel,
    closePanel,
    sendMessage,
  } = useAIChat()

  const [input, setInput] = useState('')
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [speechError, setSpeechError] = useState<string | null>(null)
  const [speechStatus, setSpeechStatus] = useState('点击麦克风即可语音提问')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const panelRef = useRef<HTMLDivElement>(null)
  const speechPrefixRef = useRef('')
  const speechShouldAutoSendRef = useRef(false)

  const visibleMessages = messages.filter(message => (
    message.role === 'user' || Boolean(message.content.trim()) || Boolean(message.options?.length)
  ))
  const lastMessage = messages[messages.length - 1]
  const shouldShowLoadingBubble = isLoading && !(lastMessage?.role === 'assistant' && lastMessage.content.trim())

  const syncComposer = useCallback((nextValue: string) => {
    setInput(nextValue)
    requestAnimationFrame(() => resizeComposer(inputRef.current))
  }, [])

  const resetComposer = useCallback(() => {
    setInput('')
    requestAnimationFrame(() => {
      if (inputRef.current) {
        inputRef.current.style.height = 'auto'
      }
    })
  }, [])

  const applySpeechTranscript = useCallback((spokenText: string) => {
    const transcript = spokenText.trim()
    const prefix = speechPrefixRef.current.trim()
    const nextValue = prefix && transcript
      ? `${prefix} ${transcript}`
      : (transcript || prefix)

    syncComposer(nextValue)
    setSpeechError(null)
    setSpeechStatus(transcript ? `语音转写中：${transcript}` : '正在听写...')

    return nextValue.trim()
  }, [syncComposer])

  const {
    isConnected: speechConnected,
    isRecording: speechRecording,
    startRecording: startSpeechRecording,
    stopRecording: stopSpeechRecording,
  } = useSpeechRecognition({
    enabled: isOpen,
    language: 'zh',
    enableVad: true,
    autoStop: true,
    autoStopDelay: 800,
    onPartial: (text: string) => {
      applySpeechTranscript(text)
    },
    onResult: (text: string) => {
      const nextValue = applySpeechTranscript(text)
      if (!speechShouldAutoSendRef.current || !nextValue || isLoading) {
        setSpeechStatus(nextValue ? '识别完成，可直接发送或继续修改' : '识别完成')
        return
      }

      speechShouldAutoSendRef.current = false
      setSpeechStatus('识别完成，正在发送...')
      resetComposer()
      sendMessage(nextValue)
    },
    onError: (error: string) => {
      speechShouldAutoSendRef.current = false
      setSpeechError(error)
      setSpeechStatus(`语音输入不可用：${error}`)
    },
  })

  const scrollMessagesToBottom = useCallback((behavior: ScrollBehavior = 'auto') => {
    const wrap = panelRef.current?.querySelector('.ai-messages .el-scrollbar__wrap') as HTMLElement | null
    if (wrap) {
      if (typeof wrap.scrollTo === 'function') {
        wrap.scrollTo({ top: wrap.scrollHeight, behavior })
      } else {
        wrap.scrollTop = wrap.scrollHeight
      }
      return
    }
    messagesEndRef.current?.scrollIntoView({ block: 'end', behavior })
  }, [])

  useEffect(() => {
    if (!isOpen) return
    const handle = (event: MouseEvent) => {
      const target = event.target as Node
      if (panelRef.current && !panelRef.current.contains(target)) {
        closePanel()
      }
    }
    document.addEventListener('pointerdown', handle)
    return () => document.removeEventListener('pointerdown', handle)
  }, [isOpen, closePanel])

  useEffect(() => {
    if (!isOpen) return
    inputRef.current?.focus()
  }, [isOpen])

  useEffect(() => {
    if (speechRecording) return
    if (speechError) return
    setSpeechStatus(speechConnected ? '点击麦克风即可语音提问' : '语音服务未连接')
  }, [speechConnected, speechError, speechRecording])

  useEffect(() => {
    if (!isOpen) return
    scrollMessagesToBottom(isLoading ? 'auto' : 'smooth')
  }, [isOpen, isLoading, messages, scrollMessagesToBottom])

  useEffect(() => {
    if (isOpen) return
    speechShouldAutoSendRef.current = false
    if (speechRecording) {
      stopSpeechRecording()
    }
  }, [isOpen, speechRecording, stopSpeechRecording])

  useEffect(() => () => {
    speechShouldAutoSendRef.current = false
    stopSpeechRecording()
  }, [stopSpeechRecording])

  const showQuickActions = !isGreeting && greetingDone && messages.every(message => message.role !== 'user')

  const handleSend = useCallback(() => {
    const text = input.trim()
    if (!text || isLoading) return
    speechShouldAutoSendRef.current = false
    setSpeechError(null)
    resetComposer()
    sendMessage(text)
  }, [input, isLoading, resetComposer, sendMessage])

  const handleVoiceToggle = useCallback(async () => {
    if (speechRecording) {
      speechShouldAutoSendRef.current = false
      stopSpeechRecording()
      return
    }

    speechPrefixRef.current = input.trim()
    speechShouldAutoSendRef.current = !speechPrefixRef.current
    setSpeechError(null)
    setSpeechStatus('正在听写...')
    await startSpeechRecording()
  }, [input, speechRecording, startSpeechRecording, stopSpeechRecording])

  const handleInput = useCallback((nextValue: string, target: HTMLTextAreaElement | null) => {
    speechShouldAutoSendRef.current = false
    setSpeechError(null)
    setSpeechStatus(speechConnected ? '点击麦克风即可语音提问' : '语音服务未连接')
    setInput(nextValue)
    resizeComposer(target)
  }, [speechConnected])

  const handleQuickAction = useCallback((value: string, autoSend: boolean) => {
    if (autoSend) {
      speechShouldAutoSendRef.current = false
      resetComposer()
      sendMessage(value)
      return
    }
    syncComposer(value)
    requestAnimationFrame(() => inputRef.current?.focus())
  }, [resetComposer, sendMessage, syncComposer])

  const toggleFullscreen = useCallback(() => {
    setIsFullscreen(value => !value)
  }, [])

  return {
    isOpen,
    isLoading,
    isGreeting,
    greetingDone,
    contextLoaded,
    openPanel,
    closePanel,
    sendMessage,
    input,
    isFullscreen,
    speechError,
    speechStatus,
    messagesEndRef,
    inputRef,
    panelRef,
    visibleMessages,
    shouldShowLoadingBubble,
    speechConnected,
    speechRecording,
    showQuickActions,
    handleSend,
    handleVoiceToggle,
    handleInput,
    handleQuickAction,
    toggleFullscreen,
  }
}
