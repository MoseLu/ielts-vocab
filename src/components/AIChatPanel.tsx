import React, { useCallback, useEffect, useRef, useState } from 'react'
import { useAIChat } from '../hooks/useAIChat'
import { useSpeechRecognition } from '../hooks/useSpeechRecognition'
import { renderJournalMarkdown } from '../lib/journalMarkdown'
import { MicroLoading } from './ui'
import { Scrollbar } from './ui/Scrollbar'

const AIRobotSVG = () => (
  <svg viewBox="0 0 1024 1024" width="22" height="22" fill="currentColor" className="ai-robot-icon">
    <path d="M512 32c91.818667 0 166.272 214.912 166.272 480l-0.085333 15.829333C675.285333 785.621333 602.026667 992 512 992c-90.88 0-164.778667-210.645333-166.272-472.064V512C345.728 246.912 420.181333 32 512 32z m0 112.213333l-1.066667 1.706667c-8.618667 14.506667-17.493333 34.133333-25.813333 58.112-27.221333 78.592-43.392 189.013333-43.392 307.968 0 118.912 16.213333 229.376 43.392 307.968 8.277333 23.936 17.194667 43.562667 25.813333 58.069333l1.066667 1.706667 1.066667-1.706667c7.893333-13.312 16.042667-30.890667 23.722666-52.181333l2.090667-5.888c27.221333-78.592 43.392-189.013333 43.392-307.968 0-118.912-16.213333-229.376-43.392-307.968a322.346667 322.346667 0 0 0-25.813333-58.069333L512 144.213333z" />
    <path d="M927.701333 272c45.909333 79.530667-102.997333 251.477333-332.544 384l-13.781333 7.850667C356.693333 790.229333 141.312 829.952 96.298667 752c-45.44-78.72 100.010667-248.021333 325.717333-380.032l6.826667-3.968c229.589333-132.565333 452.949333-175.530667 498.858666-96zM830.506667 328.106667h-2.048a322.346667 322.346667 0 0 0-63.146667 6.613333c-81.706667 15.744-185.472 56.96-288.426667 116.394667-103.04 59.477333-190.592 128.725333-245.034666 191.573333-16.597333 19.2-29.141333 36.693333-37.376 51.413333l-0.981334 1.749334 2.048 0.085333c15.445333 0.213333 34.773333-1.536 57.045334-5.546667l6.144-1.109333c81.664-15.744 185.429333-56.96 288.426666-116.394667 102.997333-59.477333 190.549333-128.725333 244.992-191.573333 16.597333-19.2 29.141333-36.693333 37.376-51.413333l0.981334-1.792z" />
    <path d="M927.701333 752c-45.909333 79.530667-269.226667 36.565333-498.858666-96l-13.653334-7.978667c-221.781333-131.413333-363.861333-298.069333-318.890666-376.021333 45.482667-78.72 264.832-37.418667 491.946666 92.032l6.912 3.968c229.546667 132.522667 378.453333 304.469333 332.544 384z m-97.194666-56.106667l-0.981334-1.792a322.346667 322.346667 0 0 0-37.376-51.370666c-54.442667-62.890667-141.994667-132.138667-244.992-191.573334-102.997333-59.477333-206.762667-100.693333-288.426666-116.437333a322.346667 322.346667 0 0 0-63.189334-6.656l-2.005333 0.042667 0.938667 1.792c7.552 13.482667 18.730667 29.354667 33.28 46.634666l4.096 4.736c54.442667 62.890667 141.994667 132.138667 244.992 191.573334 102.997333 59.477333 206.762667 100.693333 288.426666 116.437333a322.346667 322.346667 0 0 0 63.189334 6.656l2.048-0.04267z" />
  </svg>
)

const SendIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <line x1="22" y1="2" x2="11" y2="13" />
    <polygon points="22 2 15 22 11 13 2 9 22 2" />
  </svg>
)

const MicIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M12 3a3 3 0 0 0-3 3v6a3 3 0 0 0 6 0V6a3 3 0 0 0-3-3Z" />
    <path d="M19 11a7 7 0 0 1-14 0" />
    <path d="M12 18v3" />
    <path d="M8 21h8" />
  </svg>
)

const StopIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
    <rect x="6" y="6" width="12" height="12" rx="2.5" />
  </svg>
)

const CloseIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <line x1="18" y1="6" x2="6" y2="18" />
    <line x1="6" y1="6" x2="18" y2="18" />
  </svg>
)

const CopyIcon = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
  </svg>
)

const CheckIcon = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
    <polyline points="20 6 9 17 4 12" />
  </svg>
)

const FullscreenIcon = () => (
  <svg width="18" height="18" viewBox="0 0 1024 1024" fill="currentColor" aria-hidden="true">
    <path d="M896 478.72C878.336 478.72 864 464.384 864 446.72L864 200.192 594.624 469.504C582.656 481.472 563.264 481.472 551.296 469.504 539.328 457.536 539.328 438.144 551.296 426.176L818.752 158.72 576 158.72C558.336 158.72 544 144.384 544 126.72 544 109.056 558.336 94.72 576 94.72L893.056 94.72C897.728 94.016 901.568 95.232 906.112 96.768 907.584 97.28 908.992 97.792 910.336 98.496 913.152 99.904 916.48 99.648 918.784 102.016 920.448 103.68 920.064 106.112 921.28 108.032 924.288 112.064 926.208 116.736 927.04 121.856 927.104 122.752 927.552 123.456 927.488 124.288 927.552 125.12 928 125.888 928 126.72L928 446.72C928 464.384 913.664 478.72 896 478.72ZM205.248 862.72 448 862.72C465.664 862.72 480 877.056 480 894.72 480 912.384 465.664 926.72 448 926.72L130.944 926.72C126.272 927.424 122.432 926.208 117.888 924.672 116.416 924.16 115.008 923.648 113.664 922.944 110.848 921.536 107.52 921.792 105.216 919.424 103.552 917.76 103.936 915.328 102.72 913.408 99.712 909.376 97.792 904.704 96.96 899.584 96.896 898.688 96.448 897.984 96.512 897.152 96.448 896.32 96 895.552 96 894.72L96 574.72C96 557.056 110.336 542.72 128 542.72 145.664 542.72 160 557.056 160 574.72L160 821.248 429.376 551.936C441.344 539.968 460.736 539.968 472.704 551.936 484.672 563.904 484.672 583.296 472.704 595.264L205.248 862.72Z" />
  </svg>
)

const RestoreIcon = () => (
  <svg width="18" height="18" viewBox="0 0 1024 1024" fill="currentColor" aria-hidden="true">
    <path d="M108.8 561.52v101.39h181.56L64 889.26 134.74 960 361.1 733.64V915.2h101.39V561.52H108.8zM889.26 64L662.91 290.36V108.8H561.52v353.68H915.2V361.09H733.64L960 134.74 889.26 64z" />
  </svg>
)

interface CopyButtonProps {
  text: string
}

function CopyButton({ text }: CopyButtonProps) {
  const [copied, setCopied] = React.useState(false)

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 1800)
    } catch {
      const ta = document.createElement('textarea')
      ta.value = text
      ta.style.position = 'fixed'
      ta.style.opacity = '0'
      document.body.appendChild(ta)
      ta.select()
      document.execCommand('copy')
      document.body.removeChild(ta)
      setCopied(true)
      setTimeout(() => setCopied(false), 1800)
    }
  }

  return (
    <button
      className={`ai-copy-btn ${copied ? 'copied' : ''}`}
      onClick={handleCopy}
      title={copied ? '已复制' : '复制内容'}
      aria-label={copied ? '已复制' : '复制内容'}
      type="button"
    >
      {copied ? <CheckIcon /> : <CopyIcon />}
    </button>
  )
}

function PlainTextBubble({ content }: { content: string }) {
  return (
    <div className="ai-msg-bubble">
      {content.split('\n').map((line, index) => (
        <p key={`${index}-${line.slice(0, 12)}`}>{line || <br />}</p>
      ))}
    </div>
  )
}

function MarkdownBubble({ content, className = '' }: { content: string; className?: string }) {
  return (
    <div
      className={`ai-msg-bubble ai-markdown-content markdown-content ${className}`.trim()}
      dangerouslySetInnerHTML={{ __html: renderJournalMarkdown(content) }}
    />
  )
}

function AssistantBubble({ content, isStreaming = false }: { content: string; isStreaming?: boolean }) {
  return (
    <div className={`ai-assistant-bubble ${isStreaming ? 'ai-assistant-bubble--streaming' : ''}`.trim()}>
      <MarkdownBubble
        content={content}
        className={`ai-assistant-bubble__content ${isStreaming ? 'ai-assistant-bubble__content--streaming' : ''}`.trim()}
      />
      <CopyButton text={content} />
    </div>
  )
}

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
