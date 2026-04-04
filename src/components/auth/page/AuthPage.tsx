// ── Auth Page ─────────────────────────────────────────────────────────────────────

import React, { useEffect, useMemo, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../../../contexts'
import { useToast } from '../../../contexts'
import { useForm, RegisterSchema, LoginSchema } from '../../../lib'
import { UnderlineTabs } from '../../ui'

type AuthRouteMode = 'login' | 'register' | 'forgot'

// Required asterisk helper
function RequiredMark() {
  return <span className="required-mark" aria-hidden="true">*</span>
}

// ── Input with suffix icons ──────────────────────────────────────────────────────
function InputIconBtn({ onClick, children, title }: {
  onClick: () => void
  children: React.ReactNode
  title?: string
}) {
  return (
    <button
      type="button"
      className="auth-input-icon-btn"
      onClick={onClick}
      title={title}
      tabIndex={-1}
    >
      {children}
    </button>
  )
}

// Text input with clear button
function ClearableInput({ value, onChange, onBlur, placeholder, autoComplete, error, disabled }: {
  value: string
  onChange: (v: string) => void
  onBlur?: () => void
  placeholder?: string
  autoComplete?: string
  error?: string
  disabled?: boolean
}) {
  return (
    <div className="auth-input-wrapper">
      <input
        type="text"
        className={`auth-input ${error ? 'auth-input-error' : ''}`}
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onBlur={onBlur}
        autoComplete={autoComplete}
        disabled={disabled}
      />
      {value && !disabled && (
        <InputIconBtn onClick={() => onChange('')} title="清空">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="16" height="16">
            <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </InputIconBtn>
      )}
    </div>
  )
}

// Password input with show/hide toggle
function PasswordInput({ value, onChange, onBlur, placeholder, autoComplete, error }: {
  value: string
  onChange: (v: string) => void
  onBlur?: () => void
  placeholder?: string
  autoComplete?: string
  error?: string
}) {
  const [visible, setVisible] = useState(false)
  return (
    <div className="auth-input-wrapper">
      <input
        type={visible ? 'text' : 'password'}
        className={`auth-input ${error ? 'auth-input-error' : ''}`}
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onBlur={onBlur}
        autoComplete={autoComplete}
      />
      <InputIconBtn onClick={() => setVisible(v => !v)} title={visible ? '隐藏密码' : '显示密码'}>
        {visible ? (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="16" height="16">
            <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/>
            <line x1="1" y1="1" x2="23" y2="23"/>
          </svg>
        ) : (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="16" height="16">
            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
            <circle cx="12" cy="12" r="3"/>
          </svg>
        )}
      </InputIconBtn>
    </div>
  )
}

function FormField({ label, required, children, error }: {
  label: string
  required?: boolean
  children: React.ReactNode
  error?: string
}) {
  return (
    <div className="auth-form-field">
      <label className="auth-form-label">
        {label}
        {required && <RequiredMark />}
      </label>
      {children}
      {/* Always rendered to prevent layout jump; text only visible when error exists */}
      <span className="field-error">{error ?? '\u00a0'}</span>
    </div>
  )
}

export default function AuthPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { login, register, sendForgotPasswordCode, resetPassword } = useAuth()
  const { showToast } = useToast()
  const mode = useMemo<AuthRouteMode>(() => {
    if (location.pathname === '/register') return 'register'
    if (location.pathname === '/forgot-password') return 'forgot'
    return 'login'
  }, [location.pathname])
  const authTabValue = mode === 'register' ? 'register' : 'login'
  // forgot password state
  const [fpEmail, setFpEmail] = useState('')
  const [fpEmailSent, setFpEmailSent] = useState(false)
  const [fpSending, setFpSending] = useState(false)
  const [fpCode, setFpCode] = useState('')
  const [fpPassword, setFpPassword] = useState('')
  const [fpConfirm, setFpConfirm] = useState('')
  const [fpError, setFpError] = useState('')
  const [fpSubmitting, setFpSubmitting] = useState(false)
  const [showFpPassword, setShowFpPassword] = useState(false)
  const [showFpConfirm, setShowFpConfirm] = useState(false)

  useEffect(() => {
    if (mode !== 'forgot') {
      setFpError('')
      setFpEmailSent(false)
    }
  }, [mode])

  const loginForm = useForm({ schema: LoginSchema })
  const registerForm = useForm({ schema: RegisterSchema })

  const handleLoginSubmit = loginForm.handleSubmit(async (values) => {
    await login(values.identifier, values.password)
    showToast('登录成功', 'success')
    navigate('/plan')
  })

  const handleRegisterSubmit = registerForm.handleSubmit(async (values) => {
    await register(values.username, values.password, values.email || '')
    showToast('注册成功', 'success')
    navigate('/plan')
  })

  // ── Forgot password handlers ──────────────────────────────────────
  const handleSendFpCode = async () => {
    if (!fpEmail || !fpEmail.includes('@')) {
      setFpError('请输入有效的邮箱地址')
      return
    }
    setFpError('')
    setFpSending(true)
    try {
      await sendForgotPasswordCode(fpEmail)
      setFpEmailSent(true)
      showToast('开发环境：验证码已写入后端日志', 'success')
    } catch (e: any) {
      setFpError(e.message || '发送失败，请稍后重试')
    } finally {
      setFpSending(false)
    }
  }

  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault()
    setFpError('')
    if (!fpCode || fpCode.length !== 6) { setFpError('请输入 6 位验证码'); return }
    if (!fpPassword || fpPassword.length < 6) { setFpError('密码至少 6 个字符'); return }
    if (fpPassword !== fpConfirm) { setFpError('两次输入的密码不一致'); return }
    setFpSubmitting(true)
    try {
      await resetPassword(fpEmail, fpCode, fpPassword)
      showToast('密码重置成功，请登录', 'success')
      navigate('/login')
      setFpEmail(''); setFpCode(''); setFpPassword(''); setFpConfirm('')
      setFpEmailSent(false)
    } catch (e: any) {
      setFpError(e.message || '重置失败，请重试')
    } finally {
      setFpSubmitting(false)
    }
  }

  return (
    <div className="auth-page special-page">
      <div className="special-page-brand">
        <img src="/images/logo.png" alt="IELTS Vocab" className="special-page-brand-logo" />
        <div className="special-page-brand-text">
          <span className="special-page-brand-title">雅思冲刺</span>
          <span className="special-page-brand-subtitle">IELTS Vocabulary</span>
        </div>
      </div>
      <div className="auth-card">
        {/* Tabs */}
        {mode !== 'forgot' && (
          <UnderlineTabs
            className="auth-tabs"
            stretch
            ariaLabel="认证页面导航"
            value={authTabValue}
            onChange={value => navigate(value === 'login' ? '/login' : '/register')}
            options={[
              { value: 'login', label: '登录' },
              { value: 'register', label: '注册' },
            ]}
          />
        )}

        {mode === 'forgot' && (
          <div className="auth-back-header">
            <button className="auth-back-btn" onClick={() => { navigate('/login'); setFpError(''); setFpEmailSent(false) }} type="button">
              ← 返回登录
            </button>
            <h2 className="auth-forgot-title">找回密码</h2>
          </div>
        )}

        {/* Login form */}
        {mode === 'login' && (
          <form onSubmit={handleLoginSubmit} noValidate>
            <FormField label="邮箱 / 用户名" required error={loginForm.getFieldError('identifier')}>
              <ClearableInput
                value={loginForm.values.identifier ?? ''}
                onChange={(v) => loginForm.setFieldValue('identifier' as any, v)}
                onBlur={() => loginForm.setFieldTouched('identifier')}
                placeholder="请输入邮箱或用户名"
                autoComplete="username"
                error={loginForm.getFieldError('identifier')}
              />
            </FormField>

            <FormField label="密码" required error={loginForm.getFieldError('password')}>
              <PasswordInput
                value={loginForm.values.password ?? ''}
                onChange={(v) => loginForm.setFieldValue('password' as any, v)}
                onBlur={() => loginForm.setFieldTouched('password')}
                placeholder="请输入密码（至少 6 位）"
                autoComplete="current-password"
                error={loginForm.getFieldError('password')}
              />
            </FormField>

            <div className="auth-forgot-row">
              <button
                type="button"
                className="auth-forgot-link"
                onClick={() => { navigate('/forgot-password'); setFpError('') }}
              >
                忘记密码？
              </button>
            </div>

            <span className="field-error">{loginForm.errors.__form ?? '\u00a0'}</span>

            <button type="submit" className="auth-btn">登录</button>
          </form>
        )}

        {/* Register form */}
        {mode === 'register' && (
          <form onSubmit={handleRegisterSubmit} noValidate>
            <FormField label="用户名" required error={registerForm.getFieldError('username')}>
              <ClearableInput
                value={registerForm.values.username ?? ''}
                onChange={(v) => registerForm.setFieldValue('username' as any, v)}
                onBlur={() => registerForm.setFieldTouched('username')}
                placeholder="请输入用户名（至少 3 个字符）"
                autoComplete="username"
                error={registerForm.getFieldError('username')}
              />
            </FormField>

            <FormField label="邮箱" error={registerForm.getFieldError('email')}>
              <div className="auth-input-wrapper">
                <input
                  type="email"
                  className={`auth-input ${registerForm.getFieldError('email') ? 'auth-input-error' : ''}`}
                  placeholder="可选，开发环境下验证码会写入后端日志"
                  value={registerForm.values.email ?? ''}
                  onChange={(e) => registerForm.setFieldValue('email' as any, e.target.value)}
                  onBlur={() => registerForm.setFieldTouched('email')}
                  autoComplete="email"
                />
              </div>
            </FormField>

            <FormField label="密码" required error={registerForm.getFieldError('password')}>
              <PasswordInput
                value={registerForm.values.password ?? ''}
                onChange={(v) => registerForm.setFieldValue('password' as any, v)}
                onBlur={() => registerForm.setFieldTouched('password')}
                placeholder="请输入密码（至少 6 位）"
                autoComplete="new-password"
                error={registerForm.getFieldError('password')}
              />
            </FormField>

            <FormField label="确认密码" required error={registerForm.getFieldError('confirmPassword')}>
              <PasswordInput
                value={registerForm.values.confirmPassword ?? ''}
                onChange={(v) => registerForm.setFieldValue('confirmPassword' as any, v)}
                onBlur={() => registerForm.setFieldTouched('confirmPassword')}
                placeholder="再次输入密码"
                autoComplete="new-password"
                error={registerForm.getFieldError('confirmPassword')}
              />
            </FormField>

            <label className="agreement-label">
              <input type="checkbox" className="agreement-checkbox" defaultChecked={true} />
              <span className="agreement-text">我已阅读并同意</span>
              <Link to="/terms" className="agreement-link" target="_blank" rel="noreferrer">《用户服务协议》</Link>
            </label>

            <span className="field-error">{registerForm.errors.__form ?? '\u00a0'}</span>

            <button type="submit" className="auth-btn">注册</button>
          </form>
        )}

        {/* Forgot password flow */}
        {mode === 'forgot' && (
          <form onSubmit={handleResetPassword} noValidate>
            <FormField label="注册邮箱" required>
              <div className="auth-code-row">
                <ClearableInput
                  value={fpEmail}
                  onChange={setFpEmail}
                  placeholder="请输入注册时使用的邮箱"
                  autoComplete="email"
                  disabled={fpEmailSent}
                />
                <button
                  type="button"
                  className="auth-send-code-btn"
                  onClick={handleSendFpCode}
                  disabled={fpSending || fpEmailSent}
                >
                  {fpSending ? '发送中…' : fpEmailSent ? '已发送' : '发送验证码'}
                </button>
              </div>
            </FormField>

            {fpEmailSent && (
              <>
                <FormField label="验证码" required>
                  <ClearableInput
                    value={fpCode}
                    onChange={setFpCode}
                    placeholder="请输入 6 位验证码"
                    disabled={fpSubmitting}
                  />
                </FormField>

                <FormField label="新密码" required>
                  <div className="auth-input-wrapper">
                    <input
                      type={showFpPassword ? 'text' : 'password'}
                      className="auth-input"
                      placeholder="请输入新密码（至少 6 位）"
                      value={fpPassword}
                      onChange={(e) => setFpPassword(e.target.value)}
                      autoComplete="new-password"
                      disabled={fpSubmitting}
                    />
                    <InputIconBtn onClick={() => setShowFpPassword(v => !v)} title={showFpPassword ? '隐藏密码' : '显示密码'}>
                      {showFpPassword ? (
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="16" height="16">
                          <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/>
                          <line x1="1" y1="1" x2="23" y2="23"/>
                        </svg>
                      ) : (
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="16" height="16">
                          <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                          <circle cx="12" cy="12" r="3"/>
                        </svg>
                      )}
                    </InputIconBtn>
                  </div>
                </FormField>

                <FormField label="确认新密码" required>
                  <div className="auth-input-wrapper">
                    <input
                      type={showFpConfirm ? 'text' : 'password'}
                      className="auth-input"
                      placeholder="再次输入新密码"
                      value={fpConfirm}
                      onChange={(e) => setFpConfirm(e.target.value)}
                      autoComplete="new-password"
                      disabled={fpSubmitting}
                    />
                    <InputIconBtn onClick={() => setShowFpConfirm(v => !v)} title={showFpConfirm ? '隐藏密码' : '显示密码'}>
                      {showFpConfirm ? (
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="16" height="16">
                          <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/>
                          <line x1="1" y1="1" x2="23" y2="23"/>
                        </svg>
                      ) : (
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="16" height="16">
                          <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                          <circle cx="12" cy="12" r="3"/>
                        </svg>
                      )}
                    </InputIconBtn>
                  </div>
                </FormField>
              </>
            )}

            <span className="field-error">{fpError || '\u00a0'}</span>

            {fpEmailSent && (
              <button type="submit" className="auth-btn" disabled={fpSubmitting}>
                {fpSubmitting ? '重置中…' : '重置密码'}
              </button>
            )}
          </form>
        )}
      </div>
    </div>
  )
}
