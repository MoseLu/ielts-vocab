import { useCallback, useEffect, useRef, useState } from 'react'
import { useAIChat } from '../../../hooks/useAIChat'
import { useSpeechRecognition } from '../../../hooks/useSpeechRecognition'
import { useSpeechWaveform } from './useSpeechWaveform'

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
const AI_INPUT_MAX_HEIGHT = 220
const SPEECH_READY_STATUS = ''
const SPEECH_DISCONNECTED_STATUS = ''
const SPEECH_RECORDING_STATUS = ''
const SPEECH_PROCESSING_STATUS = ''
const SPEECH_COMPLETED_STATUS = ''

type LauncherAction = { label: string; value: string; autoSend: boolean }

function formatSpeechDuration(totalSeconds: number) {
  const safeSeconds = Math.max(0, totalSeconds)
  const minutes = Math.floor(safeSeconds / 60)
  const seconds = safeSeconds % 60
  return `${minutes}:${seconds.toString().padStart(2, '0')}`
}

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
  const [isFullscreen, setIsFullscreen] = useState(true)
  const [isQuickActionsExpanded, setIsQuickActionsExpanded] = useState(false)
  const [speechError, setSpeechError] = useState<string | null>(null)
  const [speechStatus, setSpeechStatus] = useState(SPEECH_READY_STATUS)
  const [speechDurationSeconds, setSpeechDurationSeconds] = useState(0)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const panelRef = useRef<HTMLDivElement>(null)
  const speechPrefixRef = useRef('')
  const speechCommittedTranscriptRef = useRef('')
  const lastAppliedSpeechValueRef = useRef('')
  const speechStartedAtRef = useRef<number | null>(null)
  const {
    attachCanvas: attachSpeechWaveformCanvas,
    pushAmplitude: registerSpeechLevel,
    resetWaveform: resetSpeechWaveform,
    setWaveformRecordingState,
  } = useSpeechWaveform()

  const visibleMessages = messages.filter(message => (
    message.role === 'user' || Boolean(message.content.trim()) || Boolean(message.options?.length)
  ))
  const hasUserMessages = messages.some(message => message.role === 'user')
  const greetingMessage = messages.find(message => message.id === 'greet') ?? messages.find(message => message.role === 'assistant')
  const greetingOptions = !hasUserMessages ? greetingMessage?.options ?? [] : []
  const launcherActions: LauncherAction[] = [
    ...greetingOptions.map(option => ({ label: option, value: option, autoSend: true })),
    ...QUICK_ACTIONS.filter(action => !greetingOptions.includes(action.label) && !greetingOptions.includes(action.value)),
  ]
  const hiddenOptionsMessageId = greetingMessage?.options?.length ? greetingMessage.id : null
  const lastMessage = messages[messages.length - 1]
  const shouldShowLoadingBubble = isLoading && !(lastMessage?.role === 'assistant' && lastMessage.content.trim())

  const clearSpeechWaveState = useCallback(() => {
    resetSpeechWaveform()
  }, [resetSpeechWaveform])

  const syncComposer = useCallback((nextValue: string) => {
    setInput(nextValue)
    requestAnimationFrame(() => resizeComposer(inputRef.current))
  }, [])

  const resetComposer = useCallback(() => {
    setInput('')
    speechCommittedTranscriptRef.current = ''
    lastAppliedSpeechValueRef.current = ''
    requestAnimationFrame(() => {
      if (inputRef.current) {
        inputRef.current.style.height = 'auto'
      }
    })
  }, [])

  const buildSpeechValue = useCallback((draftTranscript = '') => (
    [speechPrefixRef.current.trim(), speechCommittedTranscriptRef.current.trim(), draftTranscript.trim()]
      .filter(Boolean)
      .join(' ')
  ), [])

  const applySpeechTranscript = useCallback((spokenText: string, isFinal = false) => {
    const transcript = spokenText.trim()
    if (!transcript) return buildSpeechValue()
    if (isFinal && transcript) {
      speechCommittedTranscriptRef.current = [speechCommittedTranscriptRef.current.trim(), transcript]
        .filter(Boolean)
        .join(' ')
    }
    const nextValue = buildSpeechValue(isFinal ? '' : transcript)

    syncComposer(nextValue)
    lastAppliedSpeechValueRef.current = nextValue.trim()
    setSpeechError(null)
    setSpeechStatus(isFinal ? SPEECH_COMPLETED_STATUS : SPEECH_RECORDING_STATUS)

    return nextValue.trim()
  }, [buildSpeechValue, syncComposer])

  const {
    isConnected: speechConnected,
    isRecording: speechRecording,
    isProcessing: speechProcessing,
    startRecording: startSpeechRecording,
    stopRecording: stopSpeechRecording,
  } = useSpeechRecognition({
    enabled: isOpen,
    language: 'zh',
    enableVad: false,
    autoStop: false,
    autoStopDelay: 800,
    enableBrowserRecognition: true,
    enableRealtimeRecognition: true,
    onPartial: (text: string) => {
      applySpeechTranscript(text)
    },
    onResult: (text: string) => {
      const nextValue = applySpeechTranscript(text, true)
      setSpeechStatus(nextValue ? SPEECH_COMPLETED_STATUS : '')
    },
    onError: (error: string) => {
      setSpeechError(error)
      setSpeechStatus(`语音输入不可用：${error}`)
      clearSpeechWaveState()
    },
    onLevel: (level: number) => {
      registerSpeechLevel(level)
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
    setIsFullscreen(true)
    inputRef.current?.focus()
  }, [isOpen])

  useEffect(() => {
    if (speechError || speechRecording || speechProcessing) return
    setSpeechStatus(current => {
      if (!speechConnected) {
        return SPEECH_DISCONNECTED_STATUS
      }

      if (
        current === SPEECH_READY_STATUS ||
        current === SPEECH_DISCONNECTED_STATUS ||
        current === SPEECH_RECORDING_STATUS ||
        current === SPEECH_COMPLETED_STATUS ||
        current === SPEECH_PROCESSING_STATUS
      ) {
        return SPEECH_READY_STATUS
      }

      return current
    })
  }, [speechConnected, speechError, speechProcessing, speechRecording])

  useEffect(() => {
    if (!isOpen) return
    scrollMessagesToBottom(isLoading ? 'auto' : 'smooth')
  }, [isOpen, isLoading, messages, scrollMessagesToBottom])

  useEffect(() => {
    if (speechRecording) {
      if (speechStartedAtRef.current === null) {
        speechStartedAtRef.current = Date.now()
      }

      const syncDuration = () => {
        if (speechStartedAtRef.current === null) return
        setSpeechDurationSeconds(Math.floor((Date.now() - speechStartedAtRef.current) / 1000))
      }

      syncDuration()
      const intervalId = window.setInterval(syncDuration, 250)
      return () => window.clearInterval(intervalId)
    }

    if (!speechProcessing) {
      speechStartedAtRef.current = null
      setSpeechDurationSeconds(0)
    }
  }, [speechProcessing, speechRecording])

  useEffect(() => {
    setWaveformRecordingState(speechRecording)
  }, [setWaveformRecordingState, speechRecording])

  useEffect(() => {
    if (isOpen) return
    speechPrefixRef.current = ''
    speechCommittedTranscriptRef.current = ''
    lastAppliedSpeechValueRef.current = ''
    clearSpeechWaveState()
    setIsQuickActionsExpanded(false)
    setSpeechError(null)
    setSpeechStatus(SPEECH_READY_STATUS)
    speechStartedAtRef.current = null
    setSpeechDurationSeconds(0)
  }, [clearSpeechWaveState, isOpen])

  useEffect(() => {
    if (!hasUserMessages) return
    setIsQuickActionsExpanded(false)
  }, [hasUserMessages])

  const showQuickActionLauncher = !isGreeting && greetingDone && !hasUserMessages
  const showQuickActions = showQuickActionLauncher && isQuickActionsExpanded

  const handleSend = useCallback(() => {
    const text = input.trim()
    if (!text || isLoading || speechRecording || speechProcessing) return
    setIsQuickActionsExpanded(false)
    setSpeechError(null)
    setSpeechStatus(speechConnected ? SPEECH_READY_STATUS : SPEECH_DISCONNECTED_STATUS)
    resetComposer()
    sendMessage(text)
  }, [
    input,
    isLoading,
    resetComposer,
    sendMessage,
    speechConnected,
    speechProcessing,
    speechRecording,
  ])

  const handleVoiceToggle = useCallback(async () => {
    if (speechProcessing) return

    if (speechRecording) {
      setSpeechError(null)
      setSpeechStatus(SPEECH_PROCESSING_STATUS)
      stopSpeechRecording()
      return
    }

    const currentInput = input.trim()
    speechPrefixRef.current = currentInput === lastAppliedSpeechValueRef.current
      ? ''
      : currentInput
    speechStartedAtRef.current = Date.now()
    speechCommittedTranscriptRef.current = ''
    clearSpeechWaveState()
    setSpeechDurationSeconds(0)
    setSpeechError(null)
    setSpeechStatus(SPEECH_RECORDING_STATUS)
    await startSpeechRecording()
  }, [
    clearSpeechWaveState,
    input,
    speechProcessing,
    speechRecording,
    startSpeechRecording,
    stopSpeechRecording,
  ])

  const handleInput = useCallback((nextValue: string, target: HTMLTextAreaElement | null) => {
    setSpeechError(null)
    setSpeechStatus(speechConnected ? SPEECH_READY_STATUS : SPEECH_DISCONNECTED_STATUS)
    if (nextValue.trim() !== lastAppliedSpeechValueRef.current) {
      lastAppliedSpeechValueRef.current = ''
    }
    setInput(nextValue)
    resizeComposer(target)
  }, [speechConnected])

  const handleQuickAction = useCallback((value: string, autoSend: boolean) => {
    setIsQuickActionsExpanded(false)
    setSpeechError(null)
    setSpeechStatus(speechConnected ? SPEECH_READY_STATUS : SPEECH_DISCONNECTED_STATUS)
    if (autoSend) {
      resetComposer()
      sendMessage(value)
      return
    }
    syncComposer(value)
    requestAnimationFrame(() => inputRef.current?.focus())
  }, [resetComposer, sendMessage, speechConnected, syncComposer])

  const toggleQuickActions = useCallback(() => {
    setIsQuickActionsExpanded(value => !value)
  }, [])

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
    speechDurationLabel: formatSpeechDuration(speechDurationSeconds),
    speechWaveformCanvasRef: attachSpeechWaveformCanvas,
    messagesEndRef,
    inputRef,
    panelRef,
    visibleMessages,
    shouldShowLoadingBubble,
    speechConnected,
    speechRecording,
    speechProcessing,
    showQuickActionLauncher,
    showQuickActions,
    isQuickActionsExpanded,
    launcherActions,
    hiddenOptionsMessageId,
    handleSend,
    handleVoiceToggle,
    handleInput,
    handleQuickAction,
    toggleQuickActions,
    toggleFullscreen,
  }
}
