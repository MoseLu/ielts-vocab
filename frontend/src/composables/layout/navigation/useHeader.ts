import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../../../contexts'
import { openGlobalWordSearch } from '../../../components/layout/navigation/globalWordSearchEvents'
import type { HeaderProps, PracticeMode } from '../../../components/layout/navigation/Header.types'

const MODE_NAMES: Record<PracticeMode, string> = {
  smart: '智能模式',
  listening: '听音选义',
  meaning: '释义拼词',
  dictation: '听写模式',
  radio: '随身听',
}

const MODE_DESCRIPTIONS: Record<PracticeMode, string> = {
  smart: '根据水平自动调整',
  listening: '听发音选中文释义',
  meaning: '看中文释义，拼英文单词',
  dictation: '听发音拼写单词',
  radio: '连续播放音频',
}

export function useHeader({ onLogout, onDayChange, onUserUpdate }: Pick<HeaderProps, 'onLogout' | 'onDayChange' | 'onUserUpdate'>) {
  const { updateUser, isAdmin } = useAuth()
  const [showDayDropdown, setShowDayDropdown] = useState(false)
  const [showHelp, setShowHelp] = useState(false)
  const [showSettings, setShowSettings] = useState(false)
  const [showAvatarUpload, setShowAvatarUpload] = useState(false)
  const [showMobileMenu, setShowMobileMenu] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()
  const dayDropdownRef = useRef<HTMLDivElement>(null)

  const mainNavItems = useMemo<Array<{ key: string; label: string; path: string }>>(() => [
    { key: 'plan', label: '学习中心', path: '/plan' },
    { key: 'books', label: '词书', path: '/books' },
    ...(isAdmin ? [{ key: 'admin', label: '管理控制台', path: '/admin' }] : []),
  ], [isAdmin])

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dayDropdownRef.current && !dayDropdownRef.current.contains(event.target as Node)) {
        setShowDayDropdown(false)
      }

      const mobileMenu = document.querySelector('.header-mobile-menu')
      const hamburgerBtn = document.querySelector('.header-hamburger')
      if (mobileMenu && hamburgerBtn && !mobileMenu.contains(event.target as Node) && !hamburgerBtn.contains(event.target as Node)) {
        setShowMobileMenu(false)
      }
    }

    document.addEventListener('pointerdown', handleClickOutside)
    return () => document.removeEventListener('pointerdown', handleClickOutside)
  }, [])

  const handleLogout = useCallback(() => {
    onLogout()
    navigate('/login')
  }, [navigate, onLogout])

  const handleDayChange = useCallback((day: number) => {
    onDayChange?.(day)
    setShowDayDropdown(false)
  }, [onDayChange])

  const handleAvatarSave = useCallback((updatedUser: HeaderProps['user']) => {
    if (!updatedUser) return
    updateUser(updatedUser as any)
    onUserUpdate?.(updatedUser)
  }, [onUserUpdate, updateUser])

  const navigateTo = useCallback((path: string) => {
    navigate(path)
  }, [navigate])

  const navigateMobile = useCallback((path: string) => {
    navigate(path)
    setShowMobileMenu(false)
  }, [navigate])

  const toggleMobileMenu = useCallback(() => {
    setShowMobileMenu(value => !value)
  }, [])

  const closeMobileMenu = useCallback(() => {
    setShowMobileMenu(false)
  }, [])

  const handleSearchOpen = useCallback(() => {
    openGlobalWordSearch()
  }, [])

  return {
    location,
    dayDropdownRef,
    mainNavItems,
    modeNames: MODE_NAMES,
    modeDescriptions: MODE_DESCRIPTIONS,
    showDayDropdown,
    showHelp,
    showSettings,
    showAvatarUpload,
    showMobileMenu,
    setShowDayDropdown,
    setShowHelp,
    setShowSettings,
    setShowAvatarUpload,
    toggleMobileMenu,
    closeMobileMenu,
    handleLogout,
    handleDayChange,
    handleAvatarSave,
    handleSearchOpen,
    navigateTo,
    navigateMobile,
  }
}
