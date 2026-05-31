import React from 'react'
import { Pressable, StyleSheet, Text, TextInput, View } from 'react-native'
import { ArrowLeft } from 'lucide-react-native'
import { theme } from '../theme'
import { OrangeLoadingMark } from './OrangeLoadingMark'

type AuthMode = 'login' | 'register' | 'forgot'

type AccountLoginPaneProps = {
  code: string
  error: string
  identifier: string
  isLoading: boolean
  mode: AuthMode
  notice: string
  onBack: () => void
  onCodeChange: (value: string) => void
  onIdentifierChange: (value: string) => void
  onModeChange: (mode: AuthMode) => void
  onPasswordChange: (value: string) => void
  onSubmit: () => void
  onUsernameChange: (value: string) => void
  password: string
  username: string
}

const modeCopy = {
  forgot: {
    hint: '输入邮箱获取验证码，再设置新密码。',
    title: '找回密码',
  },
  login: {
    hint: '输入账号后，继续今天的雅思词汇训练。',
    title: '账号登录',
  },
  register: {
    hint: '创建账号后，学习记录会和 Web 端保持一致。',
    title: '注册账号',
  },
} as const

export function AccountLoginPane({
  code,
  error,
  identifier,
  isLoading,
  mode,
  notice,
  onBack,
  onCodeChange,
  onIdentifierChange,
  onModeChange,
  onPasswordChange,
  onSubmit,
  onUsernameChange,
  password,
  username,
}: AccountLoginPaneProps) {
  const copy = modeCopy[mode]
  const submitLabel =
    mode === 'login' ? '登录开始学习' : mode === 'register' ? '注册并登录' : code ? '重置密码' : '发送验证码'

  return (
    <View style={styles.panel}>
      <Pressable accessibilityRole="button" onPress={onBack} style={styles.backButton}>
        <ArrowLeft color="#5F793A" size={22} strokeWidth={3} />
        <Text style={styles.backText}>返回</Text>
      </Pressable>
      <Text style={styles.formTitle}>{copy.title}</Text>
      <Text style={styles.formHint}>{copy.hint}</Text>
      {mode === 'register' ? (
        <TextInput
          autoCapitalize="none"
          onChangeText={onUsernameChange}
          placeholder="用户名"
          placeholderTextColor={theme.colors.textTertiary}
          style={styles.input}
          value={username}
        />
      ) : null}
      <TextInput
        autoCapitalize="none"
        onChangeText={onIdentifierChange}
        placeholder={mode === 'login' ? '用户名或邮箱' : '邮箱'}
        placeholderTextColor={theme.colors.textTertiary}
        style={styles.input}
        value={identifier}
      />
      {mode === 'forgot' ? (
        <TextInput
          autoCapitalize="none"
          onChangeText={onCodeChange}
          placeholder="验证码（留空则发送验证码）"
          placeholderTextColor={theme.colors.textTertiary}
          style={styles.input}
          value={code}
        />
      ) : null}
      <TextInput
        onChangeText={onPasswordChange}
        placeholder={mode === 'forgot' ? '新密码' : '密码'}
        placeholderTextColor={theme.colors.textTertiary}
        secureTextEntry
        style={styles.input}
        value={password}
      />
      <Pressable disabled={isLoading} onPress={onSubmit} style={[styles.submitButton, isLoading ? styles.disabled : null]}>
        {isLoading ? (
          <View style={styles.loadingRow}>
            <OrangeLoadingMark active size={28} />
            <Text style={styles.submitText}>正在进入</Text>
          </View>
        ) : (
          <Text style={styles.submitText}>{submitLabel}</Text>
        )}
      </Pressable>
      <View style={styles.modeRow}>
        <Pressable onPress={() => onModeChange(mode === 'login' ? 'register' : 'login')}>
          <Text style={styles.modeText}>{mode === 'login' ? '注册账号' : '已有账号'}</Text>
        </Pressable>
        <Pressable onPress={() => onModeChange('forgot')}>
          <Text style={styles.modeText}>忘记密码</Text>
        </Pressable>
      </View>
      {notice ? <Text style={styles.notice}>{notice}</Text> : null}
      {error ? <Text style={styles.error}>{error}</Text> : null}
    </View>
  )
}

const styles = StyleSheet.create({
  backButton: {
    alignItems: 'center',
    alignSelf: 'flex-start',
    flexDirection: 'row',
    gap: 4,
    marginBottom: theme.spacing.md,
  },
  backText: {
    color: '#5F793A',
    fontSize: theme.typography.label,
    fontWeight: '900',
  },
  disabled: {
    opacity: 0.72,
  },
  error: {
    color: theme.colors.danger,
    fontSize: theme.typography.caption,
    fontWeight: '800',
    marginTop: theme.spacing.sm,
    textAlign: 'center',
  },
  formHint: {
    color: '#6F7D43',
    fontSize: theme.typography.caption,
    fontWeight: '700',
    lineHeight: 19,
    marginTop: 4,
  },
  formTitle: {
    color: '#4F6A2D',
    fontSize: 26,
    fontWeight: '900',
  },
  input: {
    backgroundColor: theme.colors.surfaceElevated,
    borderColor: '#C7DE8B',
    borderRadius: theme.radius.pill,
    borderWidth: 1,
    color: theme.colors.text,
    fontSize: theme.typography.body,
    height: 52,
    marginTop: theme.spacing.md,
    paddingHorizontal: theme.spacing.lg,
  },
  loadingRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: theme.spacing.sm,
  },
  modeRow: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: theme.spacing.md,
  },
  modeText: {
    color: '#5F793A',
    fontSize: theme.typography.label,
    fontWeight: '900',
  },
  notice: {
    color: '#5F793A',
    fontSize: theme.typography.caption,
    fontWeight: '800',
    marginTop: theme.spacing.sm,
    textAlign: 'center',
  },
  panel: {
    backgroundColor: '#FFFDFC',
    borderTopLeftRadius: 28,
    borderTopRightRadius: 28,
    marginTop: theme.spacing.md,
    padding: theme.spacing.lg,
  },
  submitButton: {
    alignItems: 'center',
    backgroundColor: '#FFE29E',
    borderColor: '#FF9A4A',
    borderRadius: theme.radius.pill,
    borderWidth: 2,
    height: 58,
    justifyContent: 'center',
    marginTop: theme.spacing.lg,
  },
  submitText: {
    color: '#5A2E1B',
    fontSize: 18,
    fontWeight: '900',
  },
})
