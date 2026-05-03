import React from 'react'
import { StatusBar } from 'react-native'
import { RootNavigator } from './src/navigation/RootNavigator'
import { SessionProvider } from './src/state/SessionContext'
import { theme } from './src/theme'

export default function App() {
  return (
    <SessionProvider>
      <StatusBar barStyle="dark-content" backgroundColor={theme.colors.background} />
      <RootNavigator />
    </SessionProvider>
  )
}
