import React, { useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import Header from './components/Header'
import AuthPage from './components/AuthPage'
import HomePage from './components/HomePage'
import PracticePage from './components/PracticePage'
import Toast from './components/Toast'

function App() {
  const [user, setUser] = useState(null)
  const [currentDay, setCurrentDay] = useState(() => {
    const saved = localStorage.getItem('current_day')
    return saved ? parseInt(saved, 10) : null
  })
  const [mode, setMode] = useState(() => localStorage.getItem('current_mode') || 'listening')
  const [toast, setToast] = useState(null)

  useEffect(() => {
    // Check for saved session
    const savedToken = localStorage.getItem('auth_token')
    const savedUser = localStorage.getItem('auth_user')
    if (savedToken && savedUser) {
      setUser(JSON.parse(savedUser))
    }

    // Apply saved settings on startup
    const savedSettings = localStorage.getItem('app_settings')
    if (savedSettings) {
      const s = JSON.parse(savedSettings)
      document.documentElement.setAttribute('data-theme', s.darkMode ? 'dark' : 'light')
      document.documentElement.setAttribute('data-font-size', s.fontSize || 'medium')
    }
  }, [])

  const handleDayChange = (day) => {
    setCurrentDay(day)
    localStorage.setItem('current_day', day.toString())
  }

  const showToast = (message, type = 'info') => {
    setToast({ message, type })
    setTimeout(() => setToast(null), 3000)
  }

  const handleLogout = () => {
    localStorage.removeItem('auth_token')
    localStorage.removeItem('auth_user')
    setUser(null)
  }

  return (
    <Router>
      <div className="app">
        <Header
          user={user}
          currentDay={currentDay}
          mode={mode}
          onLogout={handleLogout}
          onModeChange={(m) => { setMode(m); localStorage.setItem('current_mode', m) }}
          onDayChange={handleDayChange}
        />

        <main className="main">
          <Routes>
            <Route
              path="/login"
              element={
                user ? (
                  <Navigate to="/" replace />
                ) : (
                  <AuthPage
                    onLogin={(userData) => {
                      setUser(userData)
                    }}
                    showToast={showToast}
                  />
                )
              }
            />

            <Route
              path="/"
              element={
                user ? (
                  <HomePage
                    user={user}
                    currentDay={currentDay}
                    onDayChange={handleDayChange}
                  />
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
                    onComplete={() => window.location.href = '/'}
                    onBack={() => window.location.href = '/'}
                    showToast={showToast}
                    onDayChange={handleDayChange}
                  />
                ) : (
                  <Navigate to="/login" replace />
                )
              }
            />

            <Route path="*" element={<Navigate to={user ? "/" : "/login"} replace />} />
          </Routes>
        </main>

        {toast && <Toast message={toast.message} type={toast.type} />}
      </div>
    </Router>
  )
}

export default App