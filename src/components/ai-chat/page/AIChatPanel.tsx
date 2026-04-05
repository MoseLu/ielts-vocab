import React, { useCallback, useEffect, useRef, useState } from 'react'
import { useAIChat } from '../../../hooks/useAIChat'
import { useSpeechRecognition } from '../../../hooks/useSpeechRecognition'
import {
  AIRobotSVG,
  AssistantBubble,
  CloseIcon,
  FullscreenIcon,
  MicIcon,
  PlainTextBubble,
  RestoreIcon,
  SendIcon,
  StopIcon,
} from '../panel/AIChatPanelChrome'
import { MicroLoading } from '../../ui'
import { Scrollbar } from '../../ui/Scrollbar'

const QUICK_ACTIONS: Array<{ label: string; value: string; autoSend: boolean }> = [
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

const AI_INPUT_PLACEHOLDER = '输入问题，或发送学习指令'
const AI_INPUT_MAX_HEIGHT = 120

function resizeComposer(textarea: HTMLTextAreaElement | null) {
  if (!textarea) return
  textarea.style.height = 'auto'
  textarea.style.height = `${Math.min(textarea.scrollHeight, AI_INPUT_MAX_HEIGHT)}px`
}

function AIChatPanel() {
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

  const handleKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      handleSend()
    }
  }

  const handleInput = (event: React.ChangeEvent<HTMLTextAreaElement>) => {
    speechShouldAutoSendRef.current = false
    setSpeechError(null)
    setSpeechStatus(speechConnected ? '点击麦克风即可语音提问' : '语音服务未连接')
    setInput(event.target.value)
    resizeComposer(event.target)
  }

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

  if (!isOpen) {
    return (
      <button
        className="ai-fab"
        onClick={openPanel}
        title="雅思 AI 助手"
        aria-label="打开 AI 助手"
        type="button"
      >
        <AIRobotSVG />
      </button>
    )
  }

  return (
    <div className={`ai-panel ${isFullscreen ? 'ai-panel--fullscreen' : ''}`} ref={panelRef}>
      <div className="ai-panel-header">
        <div className="ai-panel-title">
          <div className="ai-panel-avatar">
            <AIRobotSVG />
          </div>
          <div>
            <div className="ai-panel-name">雅思 AI 助手</div>
            <div className="ai-panel-status">
              {contextLoaded ? (
                <>
                  <span className="ai-status-dot online" />
                  在线
                </>
              ) : (
                <MicroLoading text="上下文加载中..." />
              )}
            </div>
          </div>
        </div>

        <div className="ai-panel-actions">
          <button
            className="ai-panel-icon-btn"
            onClick={() => setIsFullscreen((value) => !value)}
            aria-label={isFullscreen ? '还原窗口' : '全屏显示'}
            title={isFullscreen ? '还原窗口' : '全屏显示'}
            type="button"
          >
            {isFullscreen ? <RestoreIcon /> : <FullscreenIcon />}
          </button>
          <button className="ai-panel-close" onClick={closePanel} aria-label="关闭" title="关闭" type="button">
            <CloseIcon />
          </button>
        </div>
      </div>

      {isGreeting && (
        <div className="ai-greeting-loading">
          <div className="ai-greeting-skeleton" />
          <div className="ai-greeting-skeleton ai-greeting-skeleton--short" />
        </div>
      )}

      {showQuickActions && (
        <div className="ai-quick-actions">
          {QUICK_ACTIONS.map((action) => (
            <button
              key={action.label}
              className="ai-quick-btn"
              onClick={() => {
                if (!isLoading) {
                  handleQuickAction(action.value, action.autoSend)
                }
              }}
              type="button"
            >
              {action.label}
            </button>
          ))}
        </div>
      )}

      <Scrollbar className="ai-messages">
        {visibleMessages.map((message) => (
          <div
            key={message.id}
            className={`ai-msg ai-msg-${message.role} ${message.role === 'assistant' ? 'ai-msg--assistant-wide' : ''}`}
          >
            {message.role === 'assistant'
              ? <AssistantBubble content={message.content} isStreaming={Boolean(message.isStreaming)} />
              : <PlainTextBubble content={message.content} />}
            {message.options && message.options.length > 0 && (
              <div className="ai-msg-options">
                {message.options.map((option) => (
                  <button
                    key={option}
                    className="ai-option-btn"
                    onClick={() => {
                      if (!isLoading) sendMessage(option)
                    }}
                    disabled={isLoading}
                    type="button"
                  >
                    {option}
                  </button>
                ))}
              </div>
            )}
          </div>
        ))}

        {shouldShowLoadingBubble && (
          <div className="ai-msg ai-msg-assistant ai-msg--assistant-wide">
            <div className="ai-msg-bubble">
              <MicroLoading text="AI 正在思考..." className="ai-bubble-loading" tone="accent" />
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </Scrollbar>

      <div className="ai-input-stack">
        <div className="ai-input-row">
          <textarea
            ref={inputRef}
            className="ai-input"
            value={input}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            placeholder={speechRecording ? '正在听写，请稍候...' : AI_INPUT_PLACEHOLDER}
            rows={1}
            disabled={isLoading || speechRecording}
          />
          <button
            className={`ai-voice-btn ${speechRecording ? 'ai-voice-btn--recording' : ''}`.trim()}
            onClick={() => void handleVoiceToggle()}
            disabled={isLoading || (!speechConnected && !speechRecording)}
            aria-label={speechRecording ? '停止语音输入' : '开始语音输入'}
            title={speechRecording ? '停止语音输入' : (speechConnected ? '开始语音输入' : '语音服务未连接')}
            type="button"
          >
            {speechRecording ? <StopIcon /> : <MicIcon />}
          </button>
          <button
            className="ai-send-btn"
            onClick={handleSend}
            disabled={!input.trim() || isLoading || speechRecording}
            aria-label="发送消息"
            type="button"
          >
            <SendIcon />
          </button>
        </div>
        <div
          className={`ai-voice-status ${speechError ? 'ai-voice-status--error' : ''} ${speechRecording ? 'ai-voice-status--recording' : ''}`.trim()}
          aria-live="polite"
        >
          {speechStatus}
        </div>
      </div>
    </div>
  )
}

export default AIChatPanel
