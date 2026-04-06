import { useBindEmailModal } from '../../../composables/profile/page/useBindEmailModal'

interface BindEmailModalProps {
  onClose: () => void
}

export default function BindEmailModal({ onClose }: BindEmailModalProps) {
  const {
    email,
    code,
    codeSent,
    sending,
    submitting,
    error,
    countdown,
    setEmail,
    setCode,
    handleSendCode,
    handleSubmit,
  } = useBindEmailModal({ onClose })

  return (
    <div className="bind-email-overlay" onClick={onClose}>
      <div className="bind-email-modal" onClick={event => event.stopPropagation()}>
        <div className="bind-email-header">
          <h3 className="bind-email-title">绑定邮箱</h3>
          <button className="bind-email-close" onClick={onClose} type="button">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        <p className="bind-email-desc">当前开发环境验证码会写入后端日志。绑定邮箱后可用于后续找回密码和账号安全验证。</p>

        <form onSubmit={handleSubmit} noValidate>
          <div className="bind-email-field">
            <label className="bind-email-label">邮箱地址 <span className="required-mark">*</span></label>
            <div className="bind-email-row">
              <input
                type="email"
                className="auth-input"
                placeholder="请输入邮箱地址"
                value={email}
                onChange={event => setEmail(event.target.value)}
                disabled={codeSent}
                autoComplete="email"
              />
              <button
                type="button"
                className="auth-send-code-btn"
                onClick={handleSendCode}
                disabled={sending || countdown > 0}
              >
                {sending ? '发送中…' : countdown > 0 ? `${countdown}s` : codeSent ? '重新发送' : '发送验证码'}
              </button>
            </div>
          </div>

          {codeSent && (
            <div className="bind-email-field">
              <label className="bind-email-label">验证码 <span className="required-mark">*</span></label>
              <input
                type="text"
                className="auth-input"
                placeholder="请输入6位验证码"
                value={code}
                onChange={event => setCode(event.target.value)}
                maxLength={6}
                autoComplete="one-time-code"
              />
            </div>
          )}

          <p className="field-error">{error || '\u00a0'}</p>

          <div className="bind-email-actions">
            <button type="button" className="bind-email-cancel" onClick={onClose}>取消</button>
            {codeSent && (
              <button type="submit" className="auth-btn bind-email-submit" disabled={submitting}>
                {submitting ? '绑定中…' : '确认绑定'}
              </button>
            )}
          </div>
        </form>
      </div>
    </div>
  )
}
