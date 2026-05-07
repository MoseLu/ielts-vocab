import React, { useState } from 'react'
import { ActivityIndicator, Pressable, StyleSheet, Text, TextInput, View } from 'react-native'
import { useSession } from '../state/SessionContext'
import { mobileApiClient } from '../api/mobileApi'
import { theme } from '../theme'

type AuthMode = 'login' | 'register' | 'forgot'

export function LoginScreen() {
  const { isLoading, login } = useSession()
  const [mode, setMode] = useState<AuthMode>('login')
  const [identifier, setIdentifier] = useState('admin')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('admin123')
  const [code, setCode] = useState('')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const modeTitle = mode === 'login' ? '移动端内测' : mode === 'register' ? '注册账号' : '找回密码'
  const modeHint = mode === 'login' ? '继续今天的雅思词汇训练。' : '账号能力已和 Web 端对齐。'

  async function submit() {
    setError('')
    setNotice('')
    try {
      if (mode === 'register') {
        await mobileApiClient.json('/api/auth/register', {
          method: 'POST',
          body: JSON.stringify({ username: username || identifier, email: identifier, password }),
        })
        await login(identifier.trim(), password)
        return
      }
      if (mode === 'forgot') {
        const path = code ? '/api/auth/reset-password' : '/api/auth/forgot-password'
        await mobileApiClient.json(path, {
          method: 'POST',
          body: JSON.stringify(code ? { email: identifier, code, password } : { email: identifier }),
        })
        setNotice(code ? '密码已重置，请登录' : '验证码已发送')
        if (code) setMode('login')
        return
      }
      await login(identifier.trim(), password)
    } catch (err) {
      setError(err instanceof Error ? err.message : '操作失败')
    }
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.brand}>IELTS Vocab</Text>
        <Text style={styles.title}>雅思冲刺</Text>
        <Text style={styles.subtitle}>{modeHint}</Text>
      </View>
      <View style={styles.formCard}>
        <Text style={styles.formTitle}>{modeTitle}</Text>
        {mode === 'register' ? (
          <TextInput
            autoCapitalize="none"
            onChangeText={setUsername}
            placeholder="用户名"
            style={styles.input}
            value={username}
          />
        ) : null}
        <TextInput
          autoCapitalize="none"
          onChangeText={setIdentifier}
          placeholder={mode === 'login' ? '用户名或邮箱' : '邮箱'}
          style={styles.input}
          value={identifier}
        />
        {mode === 'forgot' ? (
          <TextInput
            autoCapitalize="none"
            onChangeText={setCode}
            placeholder="验证码（留空则发送验证码）"
            style={styles.input}
            value={code}
          />
        ) : null}
        <TextInput
          onChangeText={setPassword}
          placeholder={mode === 'forgot' ? '新密码' : '密码'}
          secureTextEntry
          style={styles.input}
          value={password}
        />
        {notice ? <Text style={styles.notice}>{notice}</Text> : null}
        {error ? <Text style={styles.error}>{error}</Text> : null}
        <Pressable disabled={isLoading} onPress={submit} style={styles.button}>
          {isLoading ? (
            <ActivityIndicator color={theme.colors.textInverse} />
          ) : (
            <Text style={styles.buttonText}>{mode === 'login' ? '登录' : mode === 'register' ? '注册并登录' : code ? '重置密码' : '发送验证码'}</Text>
          )}
        </Pressable>
        <View style={styles.modeRow}>
          <Pressable onPress={() => setMode(mode === 'login' ? 'register' : 'login')}>
            <Text style={styles.modeText}>{mode === 'login' ? '注册' : '返回登录'}</Text>
          </Pressable>
          <Pressable onPress={() => setMode('forgot')}>
            <Text style={styles.modeText}>忘记密码</Text>
          </Pressable>
        </View>
      </View>
    </View>
  )
}

const styles = StyleSheet.create({
  brand: {
    color: theme.colors.accent,
    fontSize: theme.typography.title,
    fontWeight: '900',
    marginBottom: theme.spacing.sm,
  },
  button: {
    alignItems: 'center',
    backgroundColor: theme.colors.accent,
    borderRadius: theme.radius.control,
    height: 48,
    justifyContent: 'center',
    marginTop: theme.spacing.md,
    shadowColor: theme.colors.shadow,
    shadowOffset: { height: 6, width: 0 },
    shadowOpacity: 0.08,
    shadowRadius: 12,
    elevation: 2,
  },
  buttonText: {
    color: theme.colors.textInverse,
    fontSize: theme.typography.body,
    fontWeight: '700',
  },
  container: {
    backgroundColor: theme.colors.background,
    flex: 1,
    padding: theme.spacing.lg,
  },
  error: {
    color: theme.colors.danger,
    marginTop: theme.spacing.sm,
  },
  formCard: {
    backgroundColor: theme.colors.surfaceElevated,
    borderColor: theme.colors.borderStrong,
    borderRadius: theme.radius.card,
    borderWidth: 1,
    elevation: 2,
    marginTop: theme.spacing.md,
    padding: theme.spacing.lg,
    shadowColor: theme.colors.shadow,
    shadowOffset: { height: 6, width: 0 },
    shadowOpacity: 0.06,
    shadowRadius: 12,
  },
  formTitle: {
    color: theme.colors.text,
    fontSize: theme.typography.title,
    fontWeight: '900',
    marginBottom: theme.spacing.sm,
  },
  header: {
    backgroundColor: theme.colors.surfaceElevated,
    borderColor: theme.colors.borderStrong,
    borderRadius: theme.radius.card,
    borderWidth: 1,
    marginTop: theme.spacing.sm,
    paddingBottom: theme.spacing.lg,
    paddingHorizontal: theme.spacing.lg,
    paddingTop: theme.spacing.lg,
    shadowColor: theme.colors.shadow,
    shadowOffset: { height: 6, width: 0 },
    shadowOpacity: 0.05,
    shadowRadius: 12,
    elevation: 2,
  },
  modeRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: theme.spacing.lg,
  },
  modeText: {
    color: theme.colors.primary,
    fontWeight: '700',
  },
  notice: {
    color: theme.colors.success,
    marginTop: theme.spacing.sm,
  },
  input: {
    backgroundColor: theme.colors.surfaceElevated,
    borderColor: theme.colors.borderStrong,
    borderRadius: theme.radius.control,
    borderWidth: 1,
    fontSize: theme.typography.body,
    height: 48,
    marginTop: theme.spacing.md,
    paddingHorizontal: theme.spacing.md,
  },
  subtitle: {
    color: theme.colors.muted,
    fontSize: theme.typography.body,
    fontWeight: '700',
    lineHeight: 23,
  },
  title: {
    color: theme.colors.text,
    fontSize: 32,
    fontWeight: '900',
    marginBottom: theme.spacing.sm,
  },
})
