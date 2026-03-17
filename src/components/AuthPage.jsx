import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

function AuthPage({ onLogin, showToast }) {
  const navigate = useNavigate()
  const [isLogin, setIsLogin] = useState(true)
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [agreement, setAgreement] = useState(false)

  // 测试账号预填写
  useEffect(() => {
    if (isLogin) {
      setEmail('test@example.com')
      setPassword('test123')
    }
  }, [isLogin])

  const handleSubmit = async (e) => {
    e.preventDefault()

    if (!isLogin && !agreement) {
      showToast('请先同意用户服务协议', 'error')
      return
    }

    if (!isLogin && password !== confirmPassword) {
      showToast('两次输入的密码不一致', 'error')
      return
    }

    try {
      const endpoint = isLogin ? '/api/auth/login' : '/api/auth/register'
      const body = isLogin
        ? { email, password }
        : { username, email, password }

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      })

      const data = await response.json()

      if (response.ok) {
        localStorage.setItem('auth_token', data.token)
        localStorage.setItem('auth_user', JSON.stringify(data.user))
        onLogin(data.user)
        showToast(isLogin ? '登录成功' : '注册成功', 'success')
        navigate('/')
      } else {
        showToast(data.error || '操作失败', 'error')
      }
    } catch (error) {
      showToast('网络错误', 'error')
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <h1 className="auth-title">{isLogin ? '登录' : '注册'}</h1>
        <p className="auth-subtitle">{isLogin ? '登录后自动同步学习进度' : '创建账号开始学习'}</p>

        {!isLogin && (
          <input
            type="text"
            className="auth-input"
            placeholder="用户名（至少3个字符）"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            minLength={3}
          />
        )}

        <input
          type="email"
          className="auth-input"
          placeholder="邮箱地址"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />

        <input
          type="password"
          className="auth-input"
          placeholder="密码（至少6位）"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          minLength={6}
          required
        />

        {!isLogin && (
          <input
            type="password"
            className="auth-input"
            placeholder="确认密码"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            minLength={6}
          />
        )}

        <button className="auth-btn" onClick={handleSubmit}>
          {isLogin ? '登录' : '注册'}
        </button>

        <button className="auth-btn secondary" onClick={() => setIsLogin(!isLogin)}>
          {isLogin ? '注册账号' : '已有账号？登录'}
        </button>

        {!isLogin && (
          <label className="agreement-label">
            <input
              type="checkbox"
              className="agreement-checkbox"
              checked={agreement}
              onChange={(e) => setAgreement(e.target.checked)}
            />
            <span className="agreement-text">我已阅读并同意</span>
            <a href="#" className="agreement-link" onClick={(e) => e.preventDefault()}>《用户服务协议》</a>
          </label>
        )}
      </div>
    </div>
  )
}

export default AuthPage