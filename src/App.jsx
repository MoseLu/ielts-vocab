import React, { useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from 'react-router-dom'
import Header from './components/Header'
import LeftSidebar from './components/LeftSidebar'
import AuthPage from './components/AuthPage'
import HomePage from './components/HomePage'
import PracticePage from './components/PracticePage'
import VocabBookPage from './components/VocabBookPage'
import ErrorsPage from './components/ErrorsPage'
import StatsPage from './components/StatsPage'
import ProfilePage from './components/ProfilePage'
import Toast from './components/Toast'

function AppInner({ user, currentDay, mode, toast, onLogin, onLogout, onDayChange, onModeChange, onUserUpdate, showToast }) {
  const location = useLocation()
  const isPractice = location.pathname === '/practice'

  return (
    <div className="app">
      {!isPractice && (
        <Header
          user={user}
          currentDay={currentDay}
          mode={mode}
          onLogout={onLogout}
          onModeChange={onModeChange}
          onDayChange={onDayChange}
          onUserUpdate={onUserUpdate}
        />
      )}

      <div className={isPractice ? 'practice-fullscreen' : 'app-body'}>
        {user && !isPractice && <LeftSidebar />}
        <main className={isPractice ? 'practice-fullscreen-main' : 'main'}>
          <Routes>
            <Route
              path="/login"
              element={
                user ? (
                  <Navigate to="/" replace />
                ) : (
                  <AuthPage onLogin={onLogin} showToast={showToast} />
                )
              }
            />

            <Route
              path="/"
              element={
                user ? (
                  <VocabBookPage />
                ) : (
                  <Navigate to="/login" replace />
                )
              }
            />

            <Route
              path="/plan"
              element={
                user ? (
                  <HomePage user={user} />
                ) : (
                  <Navigate to="/login" replace />
                )
              }
            />

            <Route
              path="/practice"
              element={
                user ? (
                  <PracticePage
                    user={user}
                    currentDay={currentDay}
                    mode={mode}
                    onModeChange={onModeChange}
                    onDayChange={onDayChange}
                    showToast={showToast}
                  />
                ) : (
                  <Navigate to="/login" replace />
                )
              }
            />

            <Route
              path="/errors"
              element={
                user ? (
                  <ErrorsPage />
                ) : (
                  <Navigate to="/login" replace />
                )
              }
            />

            <Route
              path="/stats"
              element={
                user ? (
                  <StatsPage user={user} />
                ) : (
                  <Navigate to="/login" replace />
                )
              }
            />

            <Route
              path="/profile"
              element={
                user ? (
                  <ProfilePage user={user} onLogout={onLogout} showToast={showToast} />
                ) : (
                  <Navigate to="/login" replace />
                )
              }
            />

            <Route path="*" element={<Navigate to={user ? "/" : "/login"} replace />} />
          </Routes>
        </main>
      </div>

      {toast && <Toast message={toast.message} type={toast.type} />}
    </div>
  )
}

function App() {
  const [user, setUser] = useState(null)
  const [currentDay, setCurrentDay] = useState(() => {
    const saved = localStorage.getItem('current_day')
    return saved ? parseInt(saved, 10) : null
  })
  const [mode, setMode] = useState(() => localStorage.getItem('current_mode') || 'listening')
  const [toast, setToast] = useState(null)

  useEffect(() => {
    const savedToken = localStorage.getItem('auth_token')
    const savedUser = localStorage.getItem('auth_user')
    if (savedToken && savedUser) {
      setUser(JSON.parse(savedUser))
    }

    const savedSettings = localStorage.getItem('app_settings')
    if (savedSettings) {
      const s = JSON.parse(savedSettings)
      document.documentElement.setAttribute('data-theme', s.darkMode ? 'dark' : 'light')
      document.documentElement.setAttribute('data-font-size', s.fontSize || 'medium')
    }
  }, [])

  const handleLogin = (userData) => setUser(userData)
  const handleLogout = () => {
    localStorage.removeItem('auth_token')
    localStorage.removeItem('auth_user')
    setUser(null)
  }
  const handleDayChange = (day) => {
    setCurrentDay(day)
    localStorage.setItem('current_day', day.toString())
  }
  const handleModeChange = (m) => {
    setMode(m)
    localStorage.setItem('current_mode', m)
  }
  const handleUserUpdate = (updatedUser) => {
    setUser(updatedUser)
    localStorage.setItem('auth_user', JSON.stringify(updatedUser))
  }
  const showToast = (message, type = 'info') => {
    setToast({ message, type })
    setTimeout(() => setToast(null), 3000)
  }

  return (
    <Router>
      <AppInner
        user={user}
        currentDay={currentDay}
        mode={mode}
        toast={toast}
        onLogin={handleLogin}
        onLogout={handleLogout}
        onDayChange={handleDayChange}
        onModeChange={handleModeChange}
        onUserUpdate={handleUserUpdate}
        showToast={showToast}
      />
    </Router>
  )
}

export default App
