import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react'
import { useAuth, useToast } from '../../../contexts'

interface UseBindEmailModalOptions {
  onClose: () => void
}

export function useBindEmailModal({ onClose }: UseBindEmailModalOptions) {
  const { user, sendBindEmailCode, bindEmail } = useAuth()
  const { showToast } = useToast()
  const [email, setEmail] = useState(user?.email && !user.email.endsWith('@noemail.local') ? user.email : '')
  const [code, setCode] = useState('')
  const [codeSent, setCodeSent] = useState(false)
  const [sending, setSending] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [countdown, setCountdown] = useState(0)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const clearCountdown = useCallback(() => {
    if (timerRef.current == null) return
    clearInterval(timerRef.current)
    timerRef.current = null
  }, [])

  useEffect(() => {
    return clearCountdown
  }, [clearCountdown])

  const startCountdown = useCallback(() => {
    clearCountdown()
    setCountdown(60)
    timerRef.current = setInterval(() => {
      setCountdown(value => {
        if (value <= 1) {
          clearCountdown()
          return 0
        }
        return value - 1
      })
    }, 1000)
  }, [clearCountdown])

  const handleSendCode = useCallback(async () => {
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
      showToast('开发环境：验证码已写入后端日志', 'success')
    } catch (error: unknown) {
      setError(error instanceof Error ? error.message : '发送失败，请稍后重试')
    } finally {
      setSending(false)
    }
  }, [email, sendBindEmailCode, showToast, startCountdown])

  const handleSubmit = useCallback(async (event: FormEvent) => {
    event.preventDefault()
    if (!code || code.length !== 6) {
      setError('请输入6位验证码')
      return
    }
    setError('')
    setSubmitting(true)
    try {
      await bindEmail(email, code)
      showToast('邮箱绑定成功', 'success')
      onClose()
    } catch (error: unknown) {
      setError(error instanceof Error ? error.message : '绑定失败，请重试')
    } finally {
      setSubmitting(false)
    }
  }, [bindEmail, code, email, onClose, showToast])

  return {
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
  }
}
