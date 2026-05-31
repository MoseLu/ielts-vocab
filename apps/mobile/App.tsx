import React, { useEffect } from 'react'
import { StatusBar } from 'react-native'
import { ensureWechatSdkRegistered } from './src/auth/wechatAuth'
import { RootNavigator } from './src/navigation/RootNavigator'
import { SessionProvider } from './src/state/SessionContext'
import { theme } from './src/theme'

export default function App() {
  useEffect(() => {
    void ensureWechatSdkRegistered().catch(error => {
      console.warn('WeChat SDK registration failed', error)
    })
  }, [])

  return (
    <SessionProvider>
      <StatusBar barStyle="dark-content" backgroundColor={theme.colors.background} />
      <RootNavigator />
    </SessionProvider>
  )
}
