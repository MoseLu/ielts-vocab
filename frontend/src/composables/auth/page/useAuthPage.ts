import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useAuth, useToast } from '../../../contexts'
import { LoginSchema, RegisterSchema, useForm } from '../../../lib'

export type AuthRouteMode = 'login' | 'register' | 'forgot'

export function useAuthPage() {
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

  const handleLoginSubmit = loginForm.handleSubmit(async values => {
    await login(values.identifier, values.password)
    showToast('登录成功', 'success')
    navigate('/plan')
  })

  const handleRegisterSubmit = registerForm.handleSubmit(async values => {
    await register(values.username, values.password, values.email || '')
    showToast('注册成功', 'success')
    navigate('/plan')
  })

  const handleSendFpCode = useCallback(async () => {
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
    } catch (error: unknown) {
      setFpError(error instanceof Error ? error.message : '发送失败，请稍后重试')
    } finally {
      setFpSending(false)
    }
  }, [fpEmail, sendForgotPasswordCode, showToast])

  const handleResetPassword = useCallback(async (event: FormEvent) => {
    event.preventDefault()
    setFpError('')
    if (!fpCode || fpCode.length !== 6) { setFpError('请输入 6 位验证码'); return }
    if (!fpPassword || fpPassword.length < 6) { setFpError('密码至少 6 个字符'); return }
    if (fpPassword !== fpConfirm) { setFpError('两次输入的密码不一致'); return }
    setFpSubmitting(true)
    try {
      await resetPassword(fpEmail, fpCode, fpPassword)
      showToast('密码重置成功，请登录', 'success')
      navigate('/login')
      setFpEmail('')
      setFpCode('')
      setFpPassword('')
      setFpConfirm('')
      setFpEmailSent(false)
    } catch (error: unknown) {
      setFpError(error instanceof Error ? error.message : '重置失败，请重试')
    } finally {
      setFpSubmitting(false)
    }
  }, [fpCode, fpConfirm, fpEmail, fpPassword, navigate, resetPassword, showToast])

  const handleAuthTabChange = useCallback((value: string) => {
    navigate(value === 'login' ? '/login' : '/register')
  }, [navigate])

  const handleBackToLogin = useCallback(() => {
    navigate('/login')
    setFpError('')
    setFpEmailSent(false)
  }, [navigate])

  const handleOpenForgotPassword = useCallback(() => {
    navigate('/forgot-password')
    setFpError('')
  }, [navigate])

  return {
    mode,
    authTabValue,
    loginForm,
    registerForm,
    forgotPassword: {
      email: fpEmail,
      emailSent: fpEmailSent,
      sending: fpSending,
      code: fpCode,
      password: fpPassword,
      confirm: fpConfirm,
      error: fpError,
      submitting: fpSubmitting,
      showPassword: showFpPassword,
      showConfirm: showFpConfirm,
    },
    setForgotEmail: setFpEmail,
    setForgotCode: setFpCode,
    setForgotPassword: setFpPassword,
    setForgotConfirm: setFpConfirm,
    toggleForgotPasswordVisibility: () => setShowFpPassword(value => !value),
    toggleForgotConfirmVisibility: () => setShowFpConfirm(value => !value),
    handleLoginSubmit,
    handleRegisterSubmit,
    handleSendFpCode,
    handleResetPassword,
    handleAuthTabChange,
    handleBackToLogin,
    handleOpenForgotPassword,
  }
}
