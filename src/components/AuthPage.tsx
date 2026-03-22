// ── Auth Page ─────────────────────────────────────────────────────────────────────

import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts'
import { useToast } from '../contexts'
import { useForm, RegisterSchema, LoginSchema } from '../lib'

type Tab = 'login' | 'register' | 'forgot'

// Required asterisk helper
function RequiredMark() {
  return <span className="required-mark" aria-hidden="true">*</span>
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
  const { login, register, sendForgotPasswordCode, resetPassword } = useAuth()
  const { showToast } = useToast()
  const [tab, setTab] = useState<Tab>('login')
  // forgot password state
  const [fpEmail, setFpEmail] = useState('')
  const [fpEmailSent, setFpEmailSent] = useState(false)
  const [fpSending, setFpSending] = useState(false)
  const [fpCode, setFpCode] = useState('')
  const [fpPassword, setFpPassword] = useState('')
  const [fpConfirm, setFpConfirm] = useState('')
  const [fpError, setFpError] = useState('')
  const [fpSubmitting, setFpSubmitting] = useState(false)

  const loginForm = useForm({ schema: LoginSchema })
  const registerForm = useForm({ schema: RegisterSchema })

  const handleLoginSubmit = loginForm.handleSubmit(async (values) => {
    await login(values.identifier, values.password)
    showToast('登录成功', 'success')
    navigate('/')
  })

  const handleRegisterSubmit = registerForm.handleSubmit(async (values) => {
    await register(values.username, values.password, values.email || '')
    showToast('注册成功', 'success')
    navigate('/')
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
      showToast('验证码已发送', 'success')
    } catch (e: any) {
      setFpError(e.message || '发送失败，请稍后重试')
    } finally {
      setFpSending(false)
    }
  }

  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault()
    setFpError('')
    if (!fpCode || fpCode.length !== 6) { setFpError('请输入6位验证码'); return }
    if (!fpPassword || fpPassword.length < 6) { setFpError('密码至少6个字符'); return }
    if (fpPassword !== fpConfirm) { setFpError('两次输入的密码不一致'); return }
    setFpSubmitting(true)
    try {
      await resetPassword(fpEmail, fpCode, fpPassword)
      showToast('密码重置成功，请登录', 'success')
      setTab('login')
      setFpEmail(''); setFpCode(''); setFpPassword(''); setFpConfirm('')
      setFpEmailSent(false)
    } catch (e: any) {
      setFpError(e.message || '重置失败，请重试')
    } finally {
      setFpSubmitting(false)
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        {/* Tabs */}
        {tab !== 'forgot' && (
          <div className="auth-tabs">
            <button
              className={`auth-tab ${tab === 'login' ? 'active' : ''}`}
              onClick={() => setTab('login')}
              type="button"
            >
              登录
            </button>
            <button
              className={`auth-tab ${tab === 'register' ? 'active' : ''}`}
              onClick={() => setTab('register')}
              type="button"
            >
              注册
            </button>
          </div>
        )}

        {tab === 'forgot' && (
          <div className="auth-back-header">
            <button className="auth-back-btn" onClick={() => { setTab('login'); setFpError(''); setFpEmailSent(false) }} type="button">
              ← 返回登录
            </button>
            <h2 className="auth-forgot-title">找回密码</h2>
          </div>
        )}

        {/* Login form */}
        {tab === 'login' && (
          <form onSubmit={handleLoginSubmit} noValidate>
            <FormField label="邮箱 / 用户名" required error={loginForm.getFieldError('identifier')}>
              <input
                type="text"
                className="auth-input"
                placeholder="请输入邮箱或用户名"
                value={loginForm.values.identifier ?? ''}
                onChange={(e) => loginForm.setFieldValue('identifier' as any, e.target.value)}
                onBlur={() => loginForm.setFieldTouched('identifier')}
                autoComplete="username"
              />
            </FormField>

            <FormField label="密码" required error={loginForm.getFieldError('password')}>
              <input
                type="password"
                className="auth-input"
                placeholder="请输入密码（至少6位）"
                value={loginForm.values.password ?? ''}
                onChange={(e) => loginForm.setFieldValue('password' as any, e.target.value)}
                onBlur={() => loginForm.setFieldTouched('password')}
                autoComplete="current-password"
              />
            </FormField>

            <div className="auth-forgot-row">
              <button
                type="button"
                className="auth-forgot-link"
                onClick={() => { setTab('forgot'); setFpError('') }}
              >
                忘记密码？
              </button>
            </div>

            <span className="field-error">{loginForm.errors.__form ?? '\u00a0'}</span>

            <button type="submit" className="auth-btn">登录</button>
          </form>
        )}

        {/* Register form */}
        {tab === 'register' && (
          <form onSubmit={handleRegisterSubmit} noValidate>
            <FormField label="用户名" required error={registerForm.getFieldError('username')}>
              <input
                type="text"
                className="auth-input"
                placeholder="请输入用户名（至少3个字符）"
                value={registerForm.values.username ?? ''}
                onChange={(e) => registerForm.setFieldValue('username' as any, e.target.value)}
                onBlur={() => registerForm.setFieldTouched('username')}
                autoComplete="username"
              />
            </FormField>

            <FormField label="邮箱" error={registerForm.getFieldError('email')}>
              <input
                type="email"
                className="auth-input"
                placeholder="可选，用于绑定账号和找回密码"
                value={registerForm.values.email ?? ''}
                onChange={(e) => registerForm.setFieldValue('email' as any, e.target.value)}
                onBlur={() => registerForm.setFieldTouched('email')}
                autoComplete="email"
              />
            </FormField>

            <FormField label="密码" required error={registerForm.getFieldError('password')}>
              <input
                type="password"
                className="auth-input"
                placeholder="请输入密码（至少6位）"
                value={registerForm.values.password ?? ''}
                onChange={(e) => registerForm.setFieldValue('password' as any, e.target.value)}
                onBlur={() => registerForm.setFieldTouched('password')}
                autoComplete="new-password"
              />
            </FormField>

            <FormField label="确认密码" required error={registerForm.getFieldError('confirmPassword')}>
              <input
                type="password"
                className="auth-input"
                placeholder="再次输入密码"
                value={registerForm.values.confirmPassword ?? ''}
                onChange={(e) => registerForm.setFieldValue('confirmPassword' as any, e.target.value)}
                onBlur={() => registerForm.setFieldTouched('confirmPassword')}
                autoComplete="new-password"
              />
            </FormField>

            <label className="agreement-label">
              <input type="checkbox" className="agreement-checkbox" defaultChecked={true} />
              <span className="agreement-text">我已阅读并同意</span>
              <a href="#" className="agreement-link" onClick={(e) => e.preventDefault()}>《用户服务协议》</a>
            </label>

            <span className="field-error">{registerForm.errors.__form ?? '\u00a0'}</span>

            <button type="submit" className="auth-btn">注册</button>
          </form>
        )}

        {/* Forgot password flow */}
        {tab === 'forgot' && (
          <form onSubmit={handleResetPassword} noValidate>
            <FormField label="注册邮箱" required>
              <div className="auth-code-row">
                <input
                  type="email"
                  className="auth-input"
                  placeholder="请输入注册时使用的邮箱"
                  value={fpEmail}
                  onChange={(e) => setFpEmail(e.target.value)}
                  disabled={fpEmailSent}
                  autoComplete="email"
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
                  <input
                    type="text"
                    className="auth-input"
                    placeholder="请输入6位验证码"
                    value={fpCode}
                    onChange={(e) => setFpCode(e.target.value)}
                    maxLength={6}
                    autoComplete="one-time-code"
                  />
                </FormField>

                <FormField label="新密码" required>
                  <input
                    type="password"
                    className="auth-input"
                    placeholder="请输入新密码（至少6位）"
                    value={fpPassword}
                    onChange={(e) => setFpPassword(e.target.value)}
                    autoComplete="new-password"
                  />
                </FormField>

                <FormField label="确认新密码" required>
                  <input
                    type="password"
                    className="auth-input"
                    placeholder="再次输入新密码"
                    value={fpConfirm}
                    onChange={(e) => setFpConfirm(e.target.value)}
                    autoComplete="new-password"
                  />
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
