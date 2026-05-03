import React from 'react'
import { Pressable, StyleSheet, Text } from 'react-native'
import { ScreenScaffold } from './ScreenScaffold'
import { useSession } from '../state/SessionContext'
import { theme } from '../theme'

export function ProfileScreen() {
  const { logout, user } = useSession()
  return (
    <ScreenScaffold title="我的" subtitle={user ? `当前账号：${user.username}` : '未登录'}>
      <Pressable onPress={logout} style={styles.button}>
        <Text style={styles.buttonText}>退出登录</Text>
      </Pressable>
    </ScreenScaffold>
  )
}

const styles = StyleSheet.create({
  button: {
    alignItems: 'center',
    backgroundColor: theme.colors.danger,
    borderRadius: theme.radius.control,
    height: 46,
    justifyContent: 'center',
  },
  buttonText: {
    color: theme.colors.textInverse,
    fontWeight: '700',
  },
})
