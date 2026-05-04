import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import { installChunkRecovery } from './app/chunkRecovery'
import { FrontendErrorBoundary } from './app/FrontendErrorBoundary'
import { installGlobalErrorReporting } from './lib/errorReporting'
import './styles/index.scss'

installChunkRecovery()
installGlobalErrorReporting()

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <FrontendErrorBoundary>
      <App />
    </FrontendErrorBoundary>
  </React.StrictMode>
)
