import { useCallback, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth, useToast } from '../../../contexts'

export function useProfilePage() {
  const { user, logout } = useAuth()
  const { showToast } = useToast()
  const navigate = useNavigate()
  const [showSettings, setShowSettings] = useState(false)
  const [showBindEmail, setShowBindEmail] = useState(false)

  const handleLogout = useCallback(() => {
    logout()
    navigate('/login')
  }, [logout, navigate])

  const handlePlaceholder = useCallback((label: string) => {
    showToast(`${label} — 敬请期待`, 'info')
  }, [showToast])

  const hasEmail = useMemo(() => {
    return Boolean(user?.email && user.email.trim() !== '')
  }, [user?.email])

  return {
    user,
    hasEmail,
    showSettings,
    showBindEmail,
    setShowSettings,
    openBindEmail: () => setShowBindEmail(true),
    closeBindEmail: () => setShowBindEmail(false),
    goToVocabTest: () => navigate('/vocab-test'),
    handleLogout,
    handlePlaceholder,
  }
}
