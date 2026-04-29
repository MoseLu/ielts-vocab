import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuthPage } from '../../../composables/auth/page/useAuthPage'
import { staticAssetUrl } from '../../../lib/staticAssetUrl'
import { UnderlineTabs } from '../../ui'

function RequiredMark() {
  return <span className="required-mark" aria-hidden="true">*</span>
}

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

function ClearableInput({ value, onChange, onBlur, placeholder, autoComplete, error, disabled }: {
  value: string
  onChange: (value: string) => void
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
        onChange={event => onChange(event.target.value)}
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

function PasswordInput({ value, onChange, onBlur, placeholder, autoComplete, error }: {
  value: string
  onChange: (value: string) => void
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
        onChange={event => onChange(event.target.value)}
        onBlur={onBlur}
        autoComplete={autoComplete}
      />
      <InputIconBtn onClick={() => setVisible(flag => !flag)} title={visible ? '隐藏密码' : '显示密码'}>
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
      <span className="field-error">{error ?? '\u00a0'}</span>
    </div>
  )
}

export default function AuthPage() {
  const {
    mode,
    authTabValue,
    loginForm,
    registerForm,
    forgotPassword,
    setForgotEmail,
    setForgotCode,
    setForgotPassword,
    setForgotConfirm,
    toggleForgotPasswordVisibility,
    toggleForgotConfirmVisibility,
    handleLoginSubmit,
    handleRegisterSubmit,
    handleSendFpCode,
    handleResetPassword,
    handleAuthTabChange,
    handleBackToLogin,
    handleOpenForgotPassword,
  } = useAuthPage()

  return (
    <div className="auth-page special-page">
      <div className="special-page-brand">
        <img src={staticAssetUrl('/images/logo.png')} alt="IELTS Vocab" className="special-page-brand-logo" />
        <div className="special-page-brand-text">
          <span className="special-page-brand-title">雅思冲刺</span>
          <span className="special-page-brand-subtitle">IELTS Vocabulary</span>
        </div>
      </div>
      <div className="auth-card">
        {mode !== 'forgot' && (
          <UnderlineTabs
            className="auth-tabs"
            stretch
            ariaLabel="认证页面导航"
            value={authTabValue}
            onChange={handleAuthTabChange}
            options={[
              { value: 'login', label: '登录' },
              { value: 'register', label: '注册' },
            ]}
          />
        )}

        {mode === 'forgot' && (
          <div className="auth-back-header">
            <button className="auth-back-btn" onClick={handleBackToLogin} type="button">
              ← 返回登录
            </button>
            <h2 className="auth-forgot-title">找回密码</h2>
          </div>
        )}

        {mode === 'login' && (
          <form onSubmit={handleLoginSubmit} noValidate>
            <FormField label="邮箱 / 用户名" required error={loginForm.getFieldError('identifier')}>
              <ClearableInput
                value={loginForm.values.identifier ?? ''}
                onChange={value => loginForm.setFieldValue('identifier' as any, value)}
                onBlur={() => loginForm.setFieldTouched('identifier')}
                placeholder="请输入邮箱或用户名"
                autoComplete="username"
                error={loginForm.getFieldError('identifier')}
              />
            </FormField>

            <FormField label="密码" required error={loginForm.getFieldError('password')}>
              <PasswordInput
                value={loginForm.values.password ?? ''}
                onChange={value => loginForm.setFieldValue('password' as any, value)}
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
                onClick={handleOpenForgotPassword}
              >
                忘记密码？
              </button>
            </div>

            <span className="field-error">{loginForm.errors.__form ?? '\u00a0'}</span>

            <button type="submit" className="auth-btn">登录</button>
          </form>
        )}

        {mode === 'register' && (
          <form onSubmit={handleRegisterSubmit} noValidate>
            <FormField label="用户名" required error={registerForm.getFieldError('username')}>
              <ClearableInput
                value={registerForm.values.username ?? ''}
                onChange={value => registerForm.setFieldValue('username' as any, value)}
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
                  onChange={event => registerForm.setFieldValue('email' as any, event.target.value)}
                  onBlur={() => registerForm.setFieldTouched('email')}
                  autoComplete="email"
                />
              </div>
            </FormField>

            <FormField label="密码" required error={registerForm.getFieldError('password')}>
              <PasswordInput
                value={registerForm.values.password ?? ''}
                onChange={value => registerForm.setFieldValue('password' as any, value)}
                onBlur={() => registerForm.setFieldTouched('password')}
                placeholder="请输入密码（至少 6 位）"
                autoComplete="new-password"
                error={registerForm.getFieldError('password')}
              />
            </FormField>

            <FormField label="确认密码" required error={registerForm.getFieldError('confirmPassword')}>
              <PasswordInput
                value={registerForm.values.confirmPassword ?? ''}
                onChange={value => registerForm.setFieldValue('confirmPassword' as any, value)}
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

        {mode === 'forgot' && (
          <form onSubmit={handleResetPassword} noValidate>
            <FormField label="注册邮箱" required>
              <div className="auth-code-row">
                <ClearableInput
                  value={forgotPassword.email}
                  onChange={setForgotEmail}
                  placeholder="请输入注册时使用的邮箱"
                  autoComplete="email"
                  disabled={forgotPassword.emailSent}
                />
                <button
                  type="button"
                  className="auth-send-code-btn"
                  onClick={handleSendFpCode}
                  disabled={forgotPassword.sending || forgotPassword.emailSent}
                >
                  {forgotPassword.sending ? '发送中…' : forgotPassword.emailSent ? '已发送' : '发送验证码'}
                </button>
              </div>
            </FormField>

            {forgotPassword.emailSent && (
              <>
                <FormField label="验证码" required>
                  <ClearableInput
                    value={forgotPassword.code}
                    onChange={setForgotCode}
                    placeholder="请输入 6 位验证码"
                    disabled={forgotPassword.submitting}
                  />
                </FormField>

                <FormField label="新密码" required>
                  <div className="auth-input-wrapper">
                    <input
                      type={forgotPassword.showPassword ? 'text' : 'password'}
                      className="auth-input"
                      placeholder="请输入新密码（至少 6 位）"
                      value={forgotPassword.password}
                      onChange={event => setForgotPassword(event.target.value)}
                      autoComplete="new-password"
                      disabled={forgotPassword.submitting}
                    />
                    <InputIconBtn onClick={toggleForgotPasswordVisibility} title={forgotPassword.showPassword ? '隐藏密码' : '显示密码'}>
                      {forgotPassword.showPassword ? (
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
                      type={forgotPassword.showConfirm ? 'text' : 'password'}
                      className="auth-input"
                      placeholder="再次输入新密码"
                      value={forgotPassword.confirm}
                      onChange={event => setForgotConfirm(event.target.value)}
                      autoComplete="new-password"
                      disabled={forgotPassword.submitting}
                    />
                    <InputIconBtn onClick={toggleForgotConfirmVisibility} title={forgotPassword.showConfirm ? '隐藏密码' : '显示密码'}>
                      {forgotPassword.showConfirm ? (
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

            <span className="field-error">{forgotPassword.error || '\u00a0'}</span>

            {forgotPassword.emailSent && (
              <button type="submit" className="auth-btn" disabled={forgotPassword.submitting}>
                {forgotPassword.submitting ? '重置中…' : '重置密码'}
              </button>
            )}
          </form>
        )}
      </div>
    </div>
  )
}
