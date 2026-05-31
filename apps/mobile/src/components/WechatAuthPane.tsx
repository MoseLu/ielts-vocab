import React from 'react'
import { Pressable, StyleSheet, Text, View } from 'react-native'
import { ArrowLeft, Check } from 'lucide-react-native'
import { theme } from '../theme'
import { WechatIcon } from './WechatIcon'

type WechatAuthPaneProps = {
  error: string
  isLoading: boolean
  notice: string
  onAllow: () => void
  onBack: () => void
  onDeny: () => void
}

export function WechatAuthPane({ error, isLoading, notice, onAllow, onBack, onDeny }: WechatAuthPaneProps) {
  return (
    <View style={styles.page}>
      <Pressable accessibilityRole="button" onPress={onBack} style={styles.closeButton}>
        <ArrowLeft color="#2F281F" size={22} strokeWidth={3} />
        <Text style={styles.closeText}>关闭</Text>
      </Pressable>
      <View style={styles.appRow}>
        <View style={styles.appIcon}>
          <WechatIcon size={34} />
        </View>
        <Text style={styles.appName}>雅思冲刺 申请使用</Text>
      </View>
      <Text style={styles.title}>你的微信昵称、头像</Text>
      <Text style={styles.hint}>你可以选择微信同意后继续登录</Text>
      <View style={styles.identityRow}>
        <View style={styles.avatar}>
          <WechatIcon size={38} />
        </View>
        <View style={styles.identityCopy}>
          <Text style={styles.nickname}>微信昵称</Text>
          <Text style={styles.identityHint}>微信头像与昵称</Text>
        </View>
        <Check color="#54B96B" size={28} strokeWidth={3} />
      </View>
      <View style={styles.actions}>
        <Pressable accessibilityRole="button" disabled={isLoading} onPress={onAllow} style={[styles.allowButton, isLoading ? styles.disabled : null]}>
          <Text style={styles.allowText}>{isLoading ? '授权中' : '允许'}</Text>
        </Pressable>
        <Pressable accessibilityRole="button" onPress={onDeny} style={styles.denyButton}>
          <Text style={styles.denyText}>拒绝</Text>
        </Pressable>
      </View>
      {notice ? <Text style={styles.notice}>{notice}</Text> : null}
      {error ? <Text style={styles.error}>{error}</Text> : null}
    </View>
  )
}

const styles = StyleSheet.create({
  actions: {
    gap: theme.spacing.lg,
    marginTop: 'auto',
    paddingHorizontal: theme.spacing.xl,
    paddingVertical: theme.spacing.xl,
  },
  allowButton: {
    alignItems: 'center',
    backgroundColor: '#54C26D',
    borderRadius: 10,
    height: 58,
    justifyContent: 'center',
  },
  allowText: {
    color: '#FFFFFF',
    fontSize: 20,
    fontWeight: '900',
  },
  appIcon: {
    alignItems: 'center',
    backgroundColor: '#E8F8EF',
    borderRadius: 8,
    height: 42,
    justifyContent: 'center',
    width: 42,
  },
  appName: {
    color: '#2F281F',
    fontSize: theme.typography.label,
    fontWeight: '900',
  },
  appRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: theme.spacing.sm,
    marginTop: theme.spacing.xl,
  },
  avatar: {
    alignItems: 'center',
    backgroundColor: '#E8F8EF',
    borderRadius: 12,
    height: 56,
    justifyContent: 'center',
    width: 56,
  },
  closeButton: {
    alignItems: 'center',
    alignSelf: 'flex-start',
    flexDirection: 'row',
    gap: 6,
  },
  closeText: {
    color: '#2F281F',
    fontSize: 18,
    fontWeight: '900',
  },
  denyButton: {
    alignItems: 'center',
    backgroundColor: '#F2F2F2',
    borderRadius: 10,
    height: 58,
    justifyContent: 'center',
  },
  denyText: {
    color: '#2F281F',
    fontSize: 20,
    fontWeight: '900',
  },
  disabled: {
    opacity: 0.72,
  },
  error: {
    color: theme.colors.danger,
    fontSize: theme.typography.caption,
    fontWeight: '800',
    marginBottom: theme.spacing.lg,
    textAlign: 'center',
  },
  hint: {
    color: '#B5B5B5',
    fontSize: theme.typography.body,
    fontWeight: '800',
    marginTop: theme.spacing.xl,
  },
  identityCopy: {
    flex: 1,
  },
  identityHint: {
    color: '#A9A9A9',
    fontSize: theme.typography.caption,
    fontWeight: '800',
    marginTop: 4,
  },
  identityRow: {
    alignItems: 'center',
    borderColor: '#F0F0F0',
    borderTopWidth: 1,
    flexDirection: 'row',
    gap: theme.spacing.md,
    marginTop: theme.spacing.lg,
    paddingVertical: theme.spacing.lg,
  },
  nickname: {
    color: '#2F281F',
    fontSize: 20,
    fontWeight: '900',
  },
  notice: {
    color: '#5F793A',
    fontSize: theme.typography.caption,
    fontWeight: '800',
    marginBottom: theme.spacing.lg,
    textAlign: 'center',
  },
  page: {
    backgroundColor: '#FFFFFF',
    flex: 1,
    paddingHorizontal: theme.spacing.xl,
    paddingTop: theme.spacing.xl,
  },
  title: {
    color: '#2F281F',
    fontSize: 28,
    fontWeight: '900',
    marginTop: theme.spacing.xl,
  },
})
