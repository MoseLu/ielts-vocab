import React, { useState, ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts'
import { useToast } from '../contexts'
import SettingsPanel from './SettingsPanel'

interface MenuItem {
  icon: ReactNode
  label: string
  action: () => void
}

// ── Bind Email Modal ───────────────────────────────────────────────────────────
function BindEmailModal({ onClose }: { onClose: () => void }) {
  const { user, sendBindEmailCode, bindEmail } = useAuth()
  const { showToast } = useToast()

  const [email, setEmail] = useState(user?.email && !user.email.endsWith('@noemail.local') ? user.email : '')
  const [code, setCode] = useState('')
  const [codeSent, setCodeSent] = useState(false)
  const [sending, setSending] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [countdown, setCountdown] = useState(0)

  const startCountdown = () => {
    setCountdown(60)
    const timer = setInterval(() => {
      setCountdown((n) => {
        if (n <= 1) { clearInterval(timer); return 0 }
        return n - 1
      })
    }, 1000)
  }

  const handleSendCode = async () => {
    if (!email || !email.includes('@')) {
      setError('请输入有效的邮箱地址')
      return
    }
    setError('')
    setSending(true)
    try {
      await sendBindEmailCode(email)
      setCodeSent(true)
      startCountdown()
      showToast('验证码已发送，请查收邮件', 'success')
    } catch (e: any) {
      setError(e.message || '发送失败，请稍后重试')
    } finally {
      setSending(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!code || code.length !== 6) { setError('请输入6位验证码'); return }
    setError('')
    setSubmitting(true)
    try {
      await bindEmail(email, code)
      showToast('邮箱绑定成功', 'success')
      onClose()
    } catch (e: any) {
      setError(e.message || '绑定失败，请重试')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="bind-email-overlay" onClick={onClose}>
      <div className="bind-email-modal" onClick={(e) => e.stopPropagation()}>
        <div className="bind-email-header">
          <h3 className="bind-email-title">绑定邮箱</h3>
          <button className="bind-email-close" onClick={onClose} type="button">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        <p className="bind-email-desc">绑定邮箱后可用于找回密码和账号安全验证</p>

        <form onSubmit={handleSubmit} noValidate>
          <div className="bind-email-field">
            <label className="bind-email-label">邮箱地址 <span className="required-mark">*</span></label>
            <div className="bind-email-row">
              <input
                type="email"
                className="auth-input"
                placeholder="请输入邮箱地址"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
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
                onChange={(e) => setCode(e.target.value)}
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

// ── Profile Page ───────────────────────────────────────────────────────────────
export default function ProfilePage() {
  const { user, logout } = useAuth()
  const { showToast } = useToast()
  const navigate = useNavigate()
  const [showSettings, setShowSettings] = useState<boolean>(false)
  const [showBindEmail, setShowBindEmail] = useState<boolean>(false)

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const handlePlaceholder = (label: string) => {
    showToast(`${label} — 敬请期待`, 'info')
  }

  const hasEmail = user?.email && user.email.trim() !== ''

  const menuItems: MenuItem[] = [
    {
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
          <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
          <polyline points="22,6 12,13 2,6" />
        </svg>
      ),
      label: hasEmail ? `邮箱：${user!.email}` : '绑定邮箱',
      action: () => setShowBindEmail(true),
    },
    {
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
          <circle cx="12" cy="12" r="10" />
          <path d="M12 8v4l3 3" />
        </svg>
      ),
      label: '词汇量测试',
      action: () => navigate('/vocab-test')
    },
    {
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
          <path d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.518 4.674a1 1 0 00.95.69h4.908c.969 0 1.371 1.24.588 1.81l-3.972 2.883a1 1 0 00-.364 1.118l1.518 4.674c.3.921-.755 1.688-1.538 1.118l-3.972-2.883a1 1 0 00-1.175 0l-3.972 2.883c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.364-1.118L2.083 10.1c-.783-.57-.38-1.81.588-1.81h4.908a1 1 0 00.95-.69l1.518-4.674z" />
        </svg>
      ),
      label: '功能许愿池',
      action: () => handlePlaceholder('功能许愿池')
    },
    {
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
        </svg>
      ),
      label: 'BUG反馈',
      action: () => handlePlaceholder('BUG反馈')
    },
    {
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
          <circle cx="12" cy="12" r="3" />
          <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
        </svg>
      ),
      label: '设置',
      action: () => setShowSettings(true)
    },
  ]

  return (
    <div className="profile-page">
      {/* User card */}
      <div className="profile-user-card">
        <div className="profile-avatar">
          {user?.avatar_url ? (
            <img src={user.avatar_url} alt="avatar" className="profile-avatar-img" />
          ) : (
            <img src="/assets/default-avatar.jpg" alt="默认头像" className="profile-avatar-img" />
          )}
        </div>
        <div className="profile-user-info">
          <div className="profile-username">{user?.username || '用户'}</div>
          <div className="profile-email">
            {hasEmail ? user!.email : (
              <span className="profile-email-unbound" onClick={() => setShowBindEmail(true)}>
                未绑定邮箱 — 点击绑定
              </span>
            )}
          </div>
        </div>
        <div className="profile-pro-badge">免费版</div>
      </div>

      {/* Menu list */}
      <div className="profile-menu">
        {menuItems.map((item) => (
          <button key={item.label} className="profile-menu-item" onClick={item.action}>
            <span className="profile-menu-icon">{item.icon}</span>
            <span className="profile-menu-label">{item.label}</span>
            <svg className="profile-menu-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="9 18 15 12 9 6" />
            </svg>
          </button>
        ))}

        {/* Logout */}
        <button className="profile-menu-item profile-logout-item" onClick={handleLogout}>
          <span className="profile-menu-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
              <polyline points="16 17 21 12 16 7" />
              <line x1="21" y1="12" x2="9" y2="12" />
            </svg>
          </span>
          <span className="profile-menu-label">退出登录</span>
          <svg className="profile-menu-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="9 18 15 12 9 6" />
          </svg>
        </button>
      </div>

      {showSettings && (
        <SettingsPanel showSettings={showSettings} onClose={() => setShowSettings(false)} />
      )}

      {showBindEmail && (
        <BindEmailModal onClose={() => setShowBindEmail(false)} />
      )}
    </div>
  )
}
