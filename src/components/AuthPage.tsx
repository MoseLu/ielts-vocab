// ── Auth Page ─────────────────────────────────────────────────────────────────────

import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts'
import { useToast } from '../contexts'
import { useForm, RegisterSchema, LoginSchema } from '../lib'

export default function AuthPage() {
  const navigate = useNavigate()
  const { login, register } = useAuth()
  const { showToast } = useToast()
  const [isLogin, setIsLogin] = useState(true)

  const loginForm = useForm({ schema: LoginSchema })
  const registerForm = useForm({ schema: RegisterSchema })

  const handleLoginSubmit = loginForm.handleSubmit(async (values) => {
    await login(values.email, values.password)
    showToast('登录成功', 'success')
    navigate('/')
  })

  const handleRegisterSubmit = registerForm.handleSubmit(async (values) => {
    await register(values.email, values.password, values.username)
    showToast('注册成功', 'success')
    navigate('/')
  })

  return (
    <div className="auth-page">
      <div className="auth-card">
        <h1 className="auth-title">{isLogin ? '登录' : '注册'}</h1>
        <p className="auth-subtitle">{isLogin ? '登录后自动同步学习进度' : '创建账号开始学习'}</p>

        {isLogin ? (
          <form onSubmit={handleLoginSubmit}>
            <input
              type="email"
              className="auth-input"
              placeholder="邮箱地址*"
              value={loginForm.values.email ?? ''}
              onChange={(e) => loginForm.setFieldValue('email' as any, e.target.value)}
              onBlur={() => loginForm.setFieldTouched('email')}
              required
            />
            {loginForm.getFieldError('email') && (
              <span className="field-error">{loginForm.getFieldError('email')}</span>
            )}

            <input
              type="password"
              className="auth-input"
              placeholder="密码（至少6位）*"
              value={loginForm.values.password ?? ''}
              onChange={(e) => loginForm.setFieldValue('password' as any, e.target.value)}
              onBlur={() => loginForm.setFieldTouched('password')}
              minLength={6}
              required
            />
            {loginForm.getFieldError('password') && (
              <span className="field-error">{loginForm.getFieldError('password')}</span>
            )}

            {loginForm.errors.__form && (
              <span className="field-error">{loginForm.errors.__form}</span>
            )}

            <button type="submit" className="auth-btn">登录</button>
          </form>
        ) : (
          <form onSubmit={handleRegisterSubmit}>
            <input
              type="text"
              className="auth-input"
              placeholder="用户名（至少3个字符）*"
              value={registerForm.values.username ?? ''}
              onChange={(e) => registerForm.setFieldValue('username' as any, e.target.value)}
              onBlur={() => registerForm.setFieldTouched('username')}
              minLength={3}
            />
            {registerForm.getFieldError('username') && (
              <span className="field-error">{registerForm.getFieldError('username')}</span>
            )}

            <input
              type="email"
              className="auth-input"
              placeholder="邮箱地址"
              value={registerForm.values.email ?? ''}
              onChange={(e) => registerForm.setFieldValue('email' as any, e.target.value)}
              onBlur={() => registerForm.setFieldTouched('email')}
            />
            {registerForm.getFieldError('email') && (
              <span className="field-error">{registerForm.getFieldError('email')}</span>
            )}

            <input
              type="password"
              className="auth-input"
              placeholder="密码（至少6位）*"
              value={registerForm.values.password ?? ''}
              onChange={(e) => registerForm.setFieldValue('password' as any, e.target.value)}
              onBlur={() => registerForm.setFieldTouched('password')}
              minLength={6}
              required
            />
            {registerForm.getFieldError('password') && (
              <span className="field-error">{registerForm.getFieldError('password')}</span>
            )}

            <input
              type="password"
              className="auth-input"
              placeholder="确认密码*"
              value={registerForm.values.confirmPassword ?? ''}
              onChange={(e) => registerForm.setFieldValue('confirmPassword' as any, e.target.value)}
              onBlur={() => registerForm.setFieldTouched('confirmPassword')}
              minLength={6}
              required
            />
            {registerForm.getFieldError('confirmPassword') && (
              <span className="field-error">{registerForm.getFieldError('confirmPassword')}</span>
            )}

            {registerForm.errors.__form && (
              <span className="field-error">{registerForm.errors.__form}</span>
            )}

            <label className="agreement-label">
              <input
                type="checkbox"
                className="agreement-checkbox"
                defaultChecked={true}
              />
              <span className="agreement-text">我已阅读并同意</span>
              <a href="#" className="agreement-link" onClick={(e) => e.preventDefault()}>《用户服务协议》</a>
            </label>

            <button type="submit" className="auth-btn">注册</button>
          </form>
        )}

        <button className="auth-btn secondary" onClick={() => setIsLogin(!isLogin)}>
          {isLogin ? '注册账号' : '已有账号？登录'}
        </button>
      </div>
    </div>
  )
}
