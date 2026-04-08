import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../../../contexts'
import {
  HEADER_PRACTICE_MODE_DESCRIPTIONS,
  HEADER_PRACTICE_MODE_LABELS,
} from '../../../constants/practiceModes'
import { openGlobalWordSearch } from '../../../components/layout/navigation/globalWordSearchEvents'
import type { HeaderProps, PracticeMode } from '../../../components/layout/navigation/Header.types'

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
    modeNames: HEADER_PRACTICE_MODE_LABELS as Record<PracticeMode, string>,
    modeDescriptions: HEADER_PRACTICE_MODE_DESCRIPTIONS as Record<PracticeMode, string>,
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
