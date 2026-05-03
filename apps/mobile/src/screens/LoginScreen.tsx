import React, { useState } from 'react'
import { ActivityIndicator, Pressable, StyleSheet, Text, TextInput, View } from 'react-native'
import { useSession } from '../state/SessionContext'
import { theme } from '../theme'

export function LoginScreen() {
  const { isLoading, login } = useSession()
  const [identifier, setIdentifier] = useState('admin')
  const [password, setPassword] = useState('admin123')
  const [error, setError] = useState('')

  async function submit() {
    setError('')
    try {
      await login(identifier.trim(), password)
    } catch (err) {
      setError(err instanceof Error ? err.message : '登录失败')
    }
  }

  return (
    <View style={styles.container}>
      <Text style={styles.brand}>雅思冲刺</Text>
      <Text style={styles.title}>移动端内测</Text>
      <TextInput
        autoCapitalize="none"
        onChangeText={setIdentifier}
        placeholder="用户名或邮箱"
        style={styles.input}
        value={identifier}
      />
      <TextInput
        onChangeText={setPassword}
        placeholder="密码"
        secureTextEntry
        style={styles.input}
        value={password}
      />
      {error ? <Text style={styles.error}>{error}</Text> : null}
      <Pressable disabled={isLoading} onPress={submit} style={styles.button}>
        {isLoading ? <ActivityIndicator color={theme.colors.textInverse} /> : <Text style={styles.buttonText}>登录</Text>}
      </Pressable>
    </View>
  )
}

const styles = StyleSheet.create({
  brand: {
    color: theme.colors.primary,
    fontSize: theme.typography.title,
    fontWeight: '700',
    marginBottom: theme.spacing.sm,
  },
  button: {
    alignItems: 'center',
    backgroundColor: theme.colors.primary,
    borderRadius: theme.radius.control,
    height: 48,
    justifyContent: 'center',
    marginTop: theme.spacing.md,
  },
  buttonText: {
    color: theme.colors.textInverse,
    fontSize: theme.typography.body,
    fontWeight: '700',
  },
  container: {
    backgroundColor: theme.colors.background,
    flex: 1,
    justifyContent: 'center',
    padding: theme.spacing.xl,
  },
  error: {
    color: theme.colors.danger,
    marginTop: theme.spacing.sm,
  },
  input: {
    backgroundColor: theme.colors.card,
    borderColor: theme.colors.border,
    borderRadius: theme.radius.control,
    borderWidth: 1,
    fontSize: theme.typography.body,
    height: 48,
    marginTop: theme.spacing.md,
    paddingHorizontal: theme.spacing.md,
  },
  title: {
    color: theme.colors.text,
    fontSize: theme.typography.heading,
    fontWeight: '700',
    marginBottom: theme.spacing.lg,
  },
})
