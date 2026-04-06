import type { ReactNode } from 'react'
import { BrowserRouter as Router } from 'react-router-dom'
import { AIChatProvider, AuthProvider, SettingsProvider, ToastProvider } from '../contexts'

export function AppProviders({ children }: { children: ReactNode }) {
  return (
    <Router>
      <AIChatProvider>
        <SettingsProvider>
          <ToastProvider>
            <AuthProvider>{children}</AuthProvider>
          </ToastProvider>
        </SettingsProvider>
      </AIChatProvider>
    </Router>
  )
}
