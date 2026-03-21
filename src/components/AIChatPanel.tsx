import React, { useState, useRef, useEffect, useCallback } from 'react'
import { useAIChat, GeneratedBook } from '../hooks/useAIChat'

// Inline SVG icons
const AIRobotSVG = () => (
  <svg viewBox="0 0 1024 1024" width="22" height="22" fill="currentColor" style={{ display: 'block' }}>
    <path d="M512 32c91.818667 0 166.272 214.912 166.272 480l-0.085333 15.829333C675.285333 785.621333 602.026667 992 512 992c-90.88 0-164.778667-210.645333-166.272-472.064V512C345.728 246.912 420.181333 32 512 32z m0 112.213333l-1.066667 1.706667c-8.618667 14.506667-17.493333 34.133333-25.813333 58.112-27.221333 78.592-43.392 189.013333-43.392 307.968 0 118.912 16.213333 229.376 43.392 307.968 8.277333 23.936 17.194667 43.562667 25.813333 58.069333l1.066667 1.706667 1.066667-1.706667c7.893333-13.312 16.042667-30.890667 23.722666-52.181333l2.090667-5.888c27.221333-78.592 43.392-189.013333 43.392-307.968 0-118.912-16.213333-229.376-43.392-307.968a322.346667 322.346667 0 0 0-25.813333-58.069333L512 144.213333z" />
    <path d="M927.701333 272c45.909333 79.530667-102.997333 251.477333-332.544 384l-13.781333 7.850667C356.693333 790.229333 141.312 829.952 96.298667 752c-45.44-78.72 100.010667-248.021333 325.717333-380.032l6.826667-3.968c229.589333-132.565333 452.949333-175.530667 498.858666-96zM830.506667 328.106667h-2.048a322.346667 322.346667 0 0 0-63.146667 6.613333c-81.706667 15.744-185.472 56.96-288.426667 116.394667-103.04 59.477333-190.592 128.725333-245.034666 191.573333-16.597333 19.2-29.141333 36.693333-37.376 51.413333l-0.981334 1.749334 2.048 0.085333c15.445333 0.213333 34.773333-1.536 57.045334-5.546667l6.144-1.109333c81.664-15.744 185.429333-56.96 288.426666-116.394667 102.997333-59.477333 190.549333-128.725333 244.992-191.573333 16.597333-19.2 29.141333-36.693333 37.376-51.413333l0.981334-1.792z" />
    <path d="M927.701333 752c-45.909333 79.530667-269.226667 36.565333-498.858666-96l-13.653334-7.978667c-221.781333-131.413333-363.861333-298.069333-318.890666-376.021333 45.482667-78.72 264.832-37.418667 491.946666 92.032l6.912 3.968c229.546667 132.522667 378.453333 304.469333 332.544 384z m-97.194666-56.106667l-0.981334-1.792a322.346667 322.346667 0 0 0-37.376-51.370666c-54.442667-62.890667-141.994667-132.138667-244.992-191.573334-102.997333-59.477333-206.762667-100.693333-288.426666-116.437333a322.346667 322.346667 0 0 0-63.189334-6.656l-2.005333 0.042667 0.938667 1.792c7.552 13.482667 18.730667 29.354667 33.28 46.634666l4.096 4.736c54.442667 62.890667 141.994667 132.138667 244.992 191.573334 102.997333 59.477333 206.762667 100.693333 288.426666 116.437333a322.346667 322.346667 0 0 0 63.189334 6.656l2.048-0.04267z" />
  </svg>
)

const SendIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <line x1="22" y1="2" x2="11" y2="13"/>
    <polygon points="22 2 15 22 11 13 2 9 22 2"/>
  </svg>
)

const CloseIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <line x1="18" y1="6" x2="6" y2="18"/>
    <line x1="6" y1="6" x2="18" y2="18"/>
  </svg>
)

const LoadingDots = () => (
  <div className="ai-typing-dots">
    <span/><span/><span/>
  </div>
)

const CopyIcon = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
  </svg>
)

const CheckIcon = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
    <polyline points="20 6 9 17 4 12"/>
  </svg>
)

interface CopyButtonProps { text: string }

function CopyButton({ text }: CopyButtonProps) {
  const [copied, setCopied] = React.useState(false)

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 1800)
    } catch {
      // Fallback for older browsers
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
      className="ai-copy-btn"
      onClick={handleCopy}
      title={copied ? '已复制' : '复制内容'}
      aria-label={copied ? '已复制' : '复制内容'}
    >
      {copied ? <CheckIcon /> : <CopyIcon />}
    </button>
  )
}

function AIChatPanel() {
  const {
    messages,
    isLoading,
    isGreeting,
    isOpen,
    contextLoaded,
    openPanel,
    closePanel,
    sendMessage,
  } = useAIChat()

  const [input, setInput] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const panelRef = useRef<HTMLDivElement>(null)

  // Close on outside click
  useEffect(() => {
    if (!isOpen) return
    const handle = (e: MouseEvent) => {
      const target = e.target as Node
      if (panelRef.current && !panelRef.current.contains(target)) {
        closePanel()
      }
    }
    document.addEventListener('pointerdown', handle)
    return () => document.removeEventListener('pointerdown', handle)
  }, [isOpen, closePanel])

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  const handleSend = useCallback(() => {
    const text = input.trim()
    if (!text || isLoading) return
    setInput('')
    sendMessage(text)
  }, [input, isLoading, sendMessage])

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  // Auto-resize textarea
  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value)
    e.target.style.height = 'auto'
    e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px'
  }

  if (!isOpen) {
    return (
      <button
        className="ai-fab"
        onClick={openPanel}
        title="雅思小助手"
        aria-label="打开 AI 助手"
      >
        <AIRobotSVG />
      </button>
    )
  }

  return (
    <div className="ai-panel" ref={panelRef}>
      {/* Header */}
      <div className="ai-panel-header">
        <div className="ai-panel-title">
          <div className="ai-panel-avatar">
            <AIRobotSVG />
          </div>
          <div>
            <div className="ai-panel-name">雅思小助手</div>
            <div className="ai-panel-status">
              {contextLoaded ? (
                <><span className="ai-status-dot online"/>在线</>
              ) : (
                <><span className="ai-status-dot"/>加载中</>
              )}
            </div>
          </div>
        </div>
        <button className="ai-panel-close" onClick={closePanel} aria-label="关闭">
          <CloseIcon />
        </button>
      </div>

      {/* Greeting skeleton / quick actions */}
      {isGreeting && (
        <div className="ai-greeting-loading">
          <div className="ai-greeting-skeleton" />
          <div className="ai-greeting-skeleton ai-greeting-skeleton--short" />
        </div>
      )}
      {!messages.length && !isGreeting && (
        <div className="ai-quick-actions">
          {[
            '分析我的学习数据',
            '今日应该复习什么？',
            '生成专属复习词书',
          ].map((q) => (
            <button
              key={q}
              className="ai-quick-btn"
              onClick={() => { setInput(q); sendMessage(q) }}
            >
              {q}
            </button>
          ))}
        </div>
      )}

      {/* Messages */}
      <div className="ai-messages">
        {messages.map((msg) => (
          <div key={msg.id} className={`ai-msg ai-msg-${msg.role}`}>
            {msg.role === 'assistant' && (
              <CopyButton text={msg.content} />
            )}
            <div className="ai-msg-bubble">
              {msg.content.split('\n').map((line, i) => (
                <p key={i}>{line || <br/>}</p>
              ))}
            </div>
            {msg.options && msg.options.length > 0 && (
              <div className="ai-msg-options">
                {msg.options.map((opt) => (
                  <button
                    key={opt}
                    className="ai-option-btn"
                    onClick={() => {
                      if (!isLoading) sendMessage(opt)
                    }}
                    disabled={isLoading}
                  >
                    {opt}
                  </button>
                ))}
              </div>
            )}
          </div>
        ))}
        {isLoading && (
          <div className="ai-msg ai-msg-assistant">
            <div className="ai-msg-bubble">
              <LoadingDots />
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="ai-input-row">
        <textarea
          ref={inputRef}
          className="ai-input"
          value={input}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          placeholder="输入你的问题..."
          rows={1}
          disabled={isLoading}
        />
        <button
          className="ai-send-btn"
          onClick={handleSend}
          disabled={!input.trim() || isLoading}
          aria-label="发送"
        >
          <SendIcon />
        </button>
      </div>
    </div>
  )
}

export default AIChatPanel
