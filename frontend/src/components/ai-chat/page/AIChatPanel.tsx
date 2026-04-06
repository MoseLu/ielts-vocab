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
import {
  AI_INPUT_PLACEHOLDER,
  QUICK_ACTIONS,
  useAIChatPanel,
} from '../../../composables/ai-chat/page/useAIChatPanel'

function AIChatPanel() {
  const {
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
  } = useAIChatPanel()

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
            onClick={toggleFullscreen}
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
          {QUICK_ACTIONS.map(action => (
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
        {visibleMessages.map(message => (
          <div
            key={message.id}
            className={`ai-msg ai-msg-${message.role} ${message.role === 'assistant' ? 'ai-msg--assistant-wide' : ''}`}
          >
            {message.role === 'assistant'
              ? <AssistantBubble content={message.content} isStreaming={Boolean(message.isStreaming)} />
              : <PlainTextBubble content={message.content} />}
            {message.options && message.options.length > 0 && (
              <div className="ai-msg-options">
                {message.options.map(option => (
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
            onChange={event => handleInput(event.target.value, event.target)}
            onKeyDown={event => {
              if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault()
                handleSend()
              }
            }}
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
