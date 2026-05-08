import React, { useState } from 'react'
import {
  KeyboardAvoidingView,
  Platform,
  Pressable,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  StatusBar,
  Text,
  View,
} from 'react-native'
import { Check, UserRound } from 'lucide-react-native'
import { mobileApiClient } from '../api/mobileApi'
import { requestWechatAuthCode } from '../auth/wechatAuth'
import { AccountLoginPane } from '../components/AccountLoginPane'
import { LoginAgreementModal } from '../components/LoginAgreementModal'
import { LoginRunnerVideo } from '../components/LoginRunnerVideo'
import { OrangeLoadingMark } from '../components/OrangeLoadingMark'
import { WechatIcon } from '../components/WechatIcon'
import { WechatAuthPane } from '../components/WechatAuthPane'
import { useSession } from '../state/SessionContext'
import { theme } from '../theme'

type AuthMode = 'login' | 'register' | 'forgot'
type AuthTarget = 'account' | 'wechat'
type AuthView = 'entry' | AuthTarget

export function LoginScreen() {
  const { isLoading, login, wechatLogin } = useSession()
  const [authView, setAuthView] = useState<AuthView>('entry')
  const [entryVideoKey, setEntryVideoKey] = useState(0)
  const [mode, setMode] = useState<AuthMode>('login')
  const [identifier, setIdentifier] = useState('admin')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('admin123456')
  const [code, setCode] = useState('')
  const [agreed, setAgreed] = useState(false)
  const [agreementPromptVisible, setAgreementPromptVisible] = useState(false)
  const [pendingTarget, setPendingTarget] = useState<AuthTarget | null>(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  function resetMessage() {
    setError('')
    setNotice('')
  }

  function switchMode(nextMode: AuthMode) {
    setMode(nextMode)
    resetMessage()
    if (nextMode !== 'forgot') setCode('')
  }

  function openAuthTarget(target: AuthTarget) {
    resetMessage()
    setAuthView(target)
    if (target === 'account') switchMode('login')
  }

  function returnToEntry() {
    resetMessage()
    setAuthView('entry')
    setEntryVideoKey(value => value + 1)
  }

  function requestAuthTarget(target: AuthTarget) {
    resetMessage()
    if (!agreed) {
      setPendingTarget(target)
      setAgreementPromptVisible(true)
      return
    }
    openAuthTarget(target)
  }

  function closeAgreementPrompt() {
    setAgreementPromptVisible(false)
    setPendingTarget(null)
  }

  function continueAfterAgreement() {
    const target = pendingTarget
    setAgreed(true)
    setAgreementPromptVisible(false)
    setPendingTarget(null)
    if (target) openAuthTarget(target)
  }

  function requireAgreementForCurrentView() {
    if (agreed) return true
    setPendingTarget(authView === 'wechat' ? 'wechat' : 'account')
    setAgreementPromptVisible(true)
    return false
  }

  async function submit() {
    resetMessage()
    if (!requireAgreementForCurrentView()) return
    try {
      if (mode === 'register') {
        await mobileApiClient.json('/api/auth/register', {
          method: 'POST',
          body: JSON.stringify({ email: identifier, password, username: username || identifier }),
        })
        await login(identifier.trim(), password)
        return
      }
      if (mode === 'forgot') {
        const path = code ? '/api/auth/reset-password' : '/api/auth/forgot-password'
        await mobileApiClient.json(path, {
          method: 'POST',
          body: JSON.stringify(code ? { code, email: identifier, password } : { email: identifier }),
        })
        setNotice(code ? '密码已重置，请登录' : '验证码已发送')
        if (code) {
          setMode('login')
          setCode('')
        }
        return
      }
      await login(identifier.trim(), password)
    } catch (err) {
      setError(err instanceof Error ? err.message : '操作失败')
    }
  }

  async function handleWechatAllow() {
    resetMessage()
    if (!requireAgreementForCurrentView()) return
    try {
      const auth = await requestWechatAuthCode()
      await wechatLogin(auth.code, auth.state)
    } catch (err) {
      setError(err instanceof Error ? err.message : '微信登录失败')
    }
  }

  if (authView === 'wechat') {
    return (
      <SafeAreaView style={styles.wechatSafeArea}>
        <WechatAuthPane
          error={error}
          isLoading={isLoading}
          notice={notice}
          onAllow={handleWechatAllow}
          onBack={returnToEntry}
          onDeny={() => setAuthView('entry')}
        />
        <LoginAgreementModal
          onClose={closeAgreementPrompt}
          onContinue={continueAfterAgreement}
          visible={agreementPromptVisible}
        />
      </SafeAreaView>
    )
  }

  if (authView === 'account') {
    return (
      <SafeAreaView style={styles.accountSafeArea}>
        <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={styles.keyboard}>
          <ScrollView
            contentContainerStyle={styles.accountContent}
            keyboardDismissMode="on-drag"
            keyboardShouldPersistTaps="handled"
          >
            <AccountLoginPane
              code={code}
              error={error}
              identifier={identifier}
              isLoading={isLoading}
              mode={mode}
              notice={notice}
              onBack={returnToEntry}
              onCodeChange={setCode}
              onIdentifierChange={setIdentifier}
              onModeChange={switchMode}
              onPasswordChange={setPassword}
              onSubmit={submit}
              onUsernameChange={setUsername}
              password={password}
              username={username}
            />
          </ScrollView>
        </KeyboardAvoidingView>
        <LoginAgreementModal
          onClose={closeAgreementPrompt}
          onContinue={continueAfterAgreement}
          visible={agreementPromptVisible}
        />
      </SafeAreaView>
    )
  }

  return (
    <SafeAreaView style={styles.safeArea}>
      <StatusBar backgroundColor="#F5F9E2" barStyle="dark-content" />
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={styles.keyboard}>
        <ScrollView
          contentContainerStyle={styles.entryContent}
          keyboardDismissMode="on-drag"
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}
          style={styles.content}
        >
          <View style={styles.headerPanel}>
            <View style={styles.brandRow}>
              <View style={styles.brandMark}>
                <OrangeLoadingMark active={isLoading} size={38} />
              </View>
              <View>
                <Text style={styles.brand}>雅思冲刺</Text>
                <Text style={styles.brandSub}>把单词跑进长期记忆</Text>
              </View>
            </View>

            <Text style={styles.slogan}>今天也轻快一点</Text>
          </View>
          <View style={styles.heroSection}>
            <LoginRunnerVideo key={entryVideoKey} style={styles.runnerVideo} />
          </View>

          <View style={styles.entryPanel}>
            <Pressable
              accessibilityRole="button"
              disabled={isLoading}
              onPress={() => requestAuthTarget('wechat')}
              style={[styles.loginButton, styles.wechatButton]}
            >
              <WechatIcon size={24} />
              <Text style={styles.wechatText}>微信登录</Text>
            </Pressable>
            <Pressable
              accessibilityRole="button"
              disabled={isLoading}
              onPress={() => requestAuthTarget('account')}
              style={[styles.loginButton, styles.accountButton]}
            >
              <UserRound color="#5A2E1B" size={22} strokeWidth={2.6} />
              <Text style={styles.accountText}>账号登录</Text>
            </Pressable>
            {notice ? <Text style={styles.notice}>{notice}</Text> : null}
            {error ? <Text style={styles.error}>{error}</Text> : null}
            <Pressable accessibilityRole="checkbox" onPress={() => setAgreed(value => !value)} style={styles.agreementRow}>
              <View style={[styles.checkbox, agreed ? styles.checkboxChecked : null]}>
                {agreed ? <Check color="#FFFFFF" size={14} strokeWidth={3} /> : null}
              </View>
              <Text style={styles.agreementText}>
                我已阅读并同意 <Text style={styles.linkText}>《用户协议》</Text> 和{' '}
                <Text style={styles.linkText}>《隐私政策》</Text>
              </Text>
            </Pressable>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
      <LoginAgreementModal
        onClose={closeAgreementPrompt}
        onContinue={continueAfterAgreement}
        visible={agreementPromptVisible}
      />
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  accountButton: {
    backgroundColor: '#FFE29E',
    borderColor: '#FF9A4A',
  },
  accountContent: {
    flexGrow: 1,
    justifyContent: 'center',
  },
  accountSafeArea: {
    backgroundColor: '#FFFFFF',
    flex: 1,
  },
  accountText: {
    color: '#5A2E1B',
    fontSize: 18,
    fontWeight: '900',
  },
  agreementRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: theme.spacing.sm,
    justifyContent: 'center',
    marginTop: theme.spacing.md,
  },
  agreementText: {
    color: '#6F7D43',
    flex: 1,
    fontSize: theme.typography.caption,
    fontWeight: '700',
    lineHeight: 19,
  },
  brand: {
    color: '#5A2E1B',
    fontSize: 19,
    fontWeight: '900',
  },
  brandMark: {
    alignItems: 'center',
    backgroundColor: '#FFF0D8',
    borderColor: '#FFB45F',
    borderRadius: theme.radius.pill,
    borderWidth: 2,
    height: 52,
    justifyContent: 'center',
    width: 52,
  },
  brandRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: theme.spacing.md,
    marginBottom: theme.spacing.md,
  },
  brandSub: {
    color: theme.colors.muted,
    fontSize: theme.typography.caption,
    fontWeight: '800',
    marginTop: 2,
  },
  checkbox: {
    alignItems: 'center',
    backgroundColor: theme.colors.surfaceElevated,
    borderColor: '#8BAA58',
    borderRadius: theme.radius.pill,
    borderWidth: 2,
    height: 22,
    justifyContent: 'center',
    width: 22,
  },
  checkboxChecked: {
    backgroundColor: '#79A947',
  },
  content: {
    backgroundColor: '#F5F9E2',
    flex: 1,
  },
  entryPanel: {
    backgroundColor: '#CFE88D',
    marginTop: -2,
    paddingBottom: 34,
    paddingHorizontal: theme.spacing.lg,
    paddingTop: theme.spacing.lg,
  },
  entryContent: {
    backgroundColor: '#F5F9E2',
    flexGrow: 1,
  },
  error: {
    color: theme.colors.danger,
    fontSize: theme.typography.caption,
    fontWeight: '800',
    marginTop: theme.spacing.sm,
    textAlign: 'center',
  },
  keyboard: {
    flex: 1,
  },
  headerPanel: {
    backgroundColor: '#F5F9E2',
    paddingBottom: theme.spacing.sm,
    paddingHorizontal: theme.spacing.lg,
    paddingTop: theme.spacing.sm,
  },
  heroSection: {
    backgroundColor: '#F5F9E2',
    flex: 1,
    overflow: 'hidden',
  },
  linkText: {
    color: '#4F8C9B',
  },
  loginButton: {
    alignItems: 'center',
    borderRadius: theme.radius.pill,
    borderWidth: 2,
    flexDirection: 'row',
    gap: theme.spacing.sm,
    height: 54,
    justifyContent: 'center',
    marginBottom: theme.spacing.sm,
  },
  notice: {
    color: '#5F793A',
    fontSize: theme.typography.caption,
    fontWeight: '800',
    marginTop: theme.spacing.sm,
    textAlign: 'center',
  },
  runnerVideo: {
    flex: 1,
  },
  safeArea: {
    backgroundColor: '#F5F9E2',
    flex: 1,
  },
  slogan: {
    alignSelf: 'center',
    backgroundColor: '#E5F3B8',
    borderRadius: theme.radius.pill,
    color: '#4F6A2D',
    fontSize: 20,
    fontWeight: '900',
    paddingHorizontal: theme.spacing.lg,
    paddingVertical: theme.spacing.xs,
  },
  wechatButton: {
    backgroundColor: '#DDF5C8',
    borderColor: '#79A947',
  },
  wechatSafeArea: {
    backgroundColor: '#FFFFFF',
    flex: 1,
  },
  wechatText: {
    color: '#457A2D',
    fontSize: 18,
    fontWeight: '900',
  },
})
