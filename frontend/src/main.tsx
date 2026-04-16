import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import { installChunkRecovery } from './app/chunkRecovery'
import './styles/index.scss'

installChunkRecovery()

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
