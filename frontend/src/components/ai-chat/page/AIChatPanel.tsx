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
import { MicroLoading, Spinner } from '../../ui'
import { Scrollbar } from '../../ui/Scrollbar'
import {
  AI_INPUT_PLACEHOLDER,
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
    speechDurationLabel,
    speechWaveformCanvasRef,
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
  } = useAIChatPanel()
  const showVoiceVisualizer = speechRecording || speechProcessing
  const showSpeechStatus = Boolean(speechStatus)
  const showSpeechDuration = speechRecording || speechProcessing
  const voiceVisualizerClassName = [
    'ai-voice-visualizer',
    speechRecording ? 'ai-voice-visualizer--recording' : '',
    speechProcessing ? 'ai-voice-visualizer--processing' : '',
  ].filter(Boolean).join(' ')
  const voiceButtonClassName = [
    'ai-voice-btn',
    speechRecording ? 'ai-voice-btn--recording' : '',
    speechProcessing ? 'ai-voice-btn--processing' : '',
  ].filter(Boolean).join(' ')
  const inputShellClassName = [
    'ai-input-shell',
    speechRecording ? 'ai-input-shell--recording' : '',
    speechProcessing ? 'ai-input-shell--processing' : '',
    speechError ? 'ai-input-shell--error' : '',
  ].filter(Boolean).join(' ')

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
            aria-label={isFullscreen ? '最小化窗口' : '展开窗口'}
            title={isFullscreen ? '最小化窗口' : '展开窗口'}
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

      {showQuickActionLauncher && (
        <div className={`ai-starter-panel ${showQuickActions ? 'ai-starter-panel--expanded' : ''}`.trim()}>
          <div className="ai-starter-copy">
            <div className="ai-starter-title">不知道先问什么？</div>
            <p className="ai-starter-text">先看常见任务，再决定要不要直接开始。</p>
          </div>
          <button
            className="ai-starter-toggle"
            onClick={toggleQuickActions}
            aria-expanded={isQuickActionsExpanded}
            type="button"
          >
            {isQuickActionsExpanded ? '收起常见任务' : '看看常见任务'}
          </button>

          {showQuickActions && (
            <div className="ai-quick-actions">
              {launcherActions.map(action => (
                <button
                  key={`${action.label}-${action.value}`}
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
            {message.options && message.options.length > 0 && message.id !== hiddenOptionsMessageId && (
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
          <div className={inputShellClassName}>
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
              placeholder={speechProcessing
                ? '正在转写，请稍候...'
                : speechRecording
                  ? '正在听写，请稍候...'
                  : AI_INPUT_PLACEHOLDER}
              rows={3}
              disabled={isLoading || speechRecording || speechProcessing}
            />
            <div className={`ai-input-footer ${showVoiceVisualizer || showSpeechStatus ? 'ai-input-footer--active' : ''}`.trim()}>
              {(showVoiceVisualizer || showSpeechStatus) && (
                <div className="ai-input-footer-main">
                  {showVoiceVisualizer && (
                    <div
                      className={voiceVisualizerClassName}
                      aria-hidden="true"
                    >
                      <canvas
                        ref={speechWaveformCanvasRef}
                        className="ai-voice-visualizer__canvas"
                      />
                    </div>
                  )}
                  {showSpeechStatus && (
                    <div
                      className={[
                        'ai-voice-status',
                        speechError ? 'ai-voice-status--error' : '',
                        speechRecording ? 'ai-voice-status--recording' : '',
                        speechProcessing ? 'ai-voice-status--processing' : '',
                      ].filter(Boolean).join(' ')}
                      aria-live="polite"
                    >
                      {speechStatus}
                    </div>
                  )}
                </div>
              )}
              {showSpeechDuration && <div className="ai-voice-duration">{speechDurationLabel}</div>}
              <div className="ai-input-actions">
                <button
                  className={voiceButtonClassName}
                  onClick={() => void handleVoiceToggle()}
                  disabled={isLoading || speechProcessing || (!speechConnected && !speechRecording)}
                  aria-label={speechProcessing ? '语音转写中' : speechRecording ? '停止语音输入' : '开始语音输入'}
                  title={speechProcessing
                    ? '正在将语音转换为文字'
                    : speechRecording
                      ? '停止语音输入'
                      : (speechConnected ? '开始语音输入' : '语音服务未连接')}
                  type="button"
                >
                  {speechProcessing
                    ? <Spinner size="sm" className="ai-voice-btn-spinner" />
                    : speechRecording
                      ? <StopIcon />
                      : <MicIcon />}
                </button>
                <button
                  className="ai-send-btn"
                  onClick={handleSend}
                  disabled={!input.trim() || isLoading || speechRecording || speechProcessing}
                  aria-label="发送消息"
                  type="button"
                >
                  <SendIcon />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default AIChatPanel
