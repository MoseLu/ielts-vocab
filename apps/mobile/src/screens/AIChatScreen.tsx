import React, { useState } from 'react'
import { Bot, Sparkles } from 'lucide-react-native'
import { KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native'
import { askAi } from '../api/learnerApi'
import { StatusText } from '../components/primitives'
import type { Navigate } from '../navigation/types'
import { theme } from '../theme'

export function AIChatScreen(_props: { goBack?: () => void; navigate: Navigate }) {
  const [message, setMessage] = useState('今天我应该复习什么？')
  const [answer, setAnswer] = useState('')
  const [lastQuestion, setLastQuestion] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function submit() {
    const prompt = message.trim()
    if (!prompt) {
      setError('请输入学习问题')
      return
    }
    setLoading(true)
    setError('')
    setLastQuestion(prompt)
    try {
      const payload = await askAi(prompt)
      setAnswer(payload.answer || payload.response || payload.message || JSON.stringify(payload))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'AI 请求失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={styles.screen}>
      <View style={styles.body}>
        <StatusText error={error} loading={loading} />

        <View style={styles.chatShell}>
          <ScrollView
            contentContainerStyle={styles.threadContent}
            keyboardDismissMode="on-drag"
            keyboardShouldPersistTaps="handled"
            style={styles.thread}
          >
            <View style={[styles.bubble, styles.assistantBubble]}>
              <View style={styles.bubbleHeader}>
                <Bot color={theme.colors.accent} size={18} strokeWidth={2.2} />
                <Text style={styles.bubbleTitle}>AI 助手</Text>
              </View>
              <Text style={styles.assistantText}>可以直接问今日计划、错词解释、例句、复习顺序或者练习建议。</Text>
            </View>

            {lastQuestion ? (
              <View style={[styles.bubble, styles.userBubble]}>
                <Text style={styles.userText}>{lastQuestion}</Text>
              </View>
            ) : null}

            {answer ? (
              <View style={[styles.bubble, styles.answerBubble]}>
                <View style={styles.bubbleHeader}>
                  <Sparkles color={theme.colors.accent} size={18} strokeWidth={2.2} />
                  <Text style={styles.bubbleTitle}>回答</Text>
                </View>
                <Text style={styles.answerText}>{answer}</Text>
              </View>
            ) : (
              <View style={styles.emptyState}>
                <Text style={styles.emptyTitle}>现在就能开始问</Text>
                <Text style={styles.emptyText}>输入问题后，回答会占满中间对话区，不会再只挤在半屏上。</Text>
              </View>
            )}
          </ScrollView>

          <View style={styles.composer}>
            <TextInput
              multiline
              onChangeText={setMessage}
              placeholder="比如：今天先复习错词还是先做听写？"
              placeholderTextColor={theme.colors.textTertiary}
              scrollEnabled={false}
              style={styles.input}
              textAlignVertical="top"
              value={message}
            />
            <Pressable
              accessibilityRole="button"
              disabled={loading}
              onPress={() => void submit()}
              style={[styles.sendButton, loading ? styles.sendButtonDisabled : null]}
            >
              <Text style={styles.sendText}>{loading ? '整理中...' : '发送'}</Text>
            </Pressable>
          </View>
        </View>
      </View>
    </KeyboardAvoidingView>
  )
}

const styles = StyleSheet.create({
  answerBubble: {
    backgroundColor: theme.colors.surfaceElevated,
    borderColor: theme.colors.borderStrong,
  },
  answerText: {
    color: theme.colors.text,
    fontSize: theme.typography.body,
    lineHeight: 24,
  },
  assistantBubble: {
    backgroundColor: theme.colors.accentSoft,
    borderColor: 'rgba(255,126,54,0.18)',
  },
  assistantText: {
    color: theme.colors.text,
    fontSize: theme.typography.label,
    lineHeight: 22,
  },
  body: {
    flex: 1,
    paddingHorizontal: theme.spacing.lg,
    paddingTop: theme.spacing.lg,
    paddingBottom: theme.spacing.lg,
  },
  bubble: {
    borderRadius: theme.radius.card,
    borderWidth: 1,
    padding: theme.spacing.lg,
    shadowColor: theme.colors.shadow,
    shadowOffset: { height: 6, width: 0 },
    shadowOpacity: 0.05,
    shadowRadius: 12,
    elevation: 2,
  },
  bubbleHeader: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: theme.spacing.xs,
    marginBottom: theme.spacing.sm,
  },
  bubbleTitle: {
    color: theme.colors.text,
    fontSize: theme.typography.label,
    fontWeight: '900',
  },
  chatShell: {
    flex: 1,
  },
  composer: {
    backgroundColor: theme.colors.surfaceElevated,
    borderColor: theme.colors.borderStrong,
    borderRadius: theme.radius.card,
    borderWidth: 1,
    padding: theme.spacing.md,
    shadowColor: theme.colors.shadow,
    shadowOffset: { height: 6, width: 0 },
    shadowOpacity: 0.06,
    shadowRadius: 16,
    elevation: 2,
  },
  emptyState: {
    alignItems: 'center',
    backgroundColor: theme.colors.surfaceInset,
    borderRadius: theme.radius.card,
    justifyContent: 'center',
    minHeight: 168,
    paddingHorizontal: theme.spacing.lg,
    paddingVertical: theme.spacing.xl,
  },
  emptyText: {
    color: theme.colors.muted,
    fontSize: theme.typography.label,
    lineHeight: 22,
    textAlign: 'center',
  },
  emptyTitle: {
    color: theme.colors.text,
    fontSize: theme.typography.title,
    fontWeight: '900',
    marginBottom: theme.spacing.xs,
  },
  input: {
    backgroundColor: theme.colors.surfaceInset,
    borderColor: theme.colors.border,
    borderRadius: theme.radius.control,
    borderWidth: 1,
    color: theme.colors.text,
    fontSize: theme.typography.body,
    maxHeight: 140,
    minHeight: 92,
    paddingHorizontal: theme.spacing.md,
    paddingTop: theme.spacing.md,
  },
  screen: {
    backgroundColor: theme.colors.background,
    flex: 1,
  },
  sendButton: {
    alignItems: 'center',
    backgroundColor: theme.colors.accent,
    borderRadius: theme.radius.control,
    justifyContent: 'center',
    minHeight: 50,
    marginTop: theme.spacing.sm,
  },
  sendButtonDisabled: {
    opacity: 0.65,
  },
  sendText: {
    color: theme.colors.textInverse,
    fontSize: theme.typography.label,
    fontWeight: '900',
  },
  thread: {
    flex: 1,
  },
  threadContent: {
    flexGrow: 1,
    gap: theme.spacing.md,
    paddingBottom: theme.spacing.md,
  },
  userBubble: {
    alignSelf: 'flex-end',
    backgroundColor: theme.colors.infoSoft,
    borderColor: 'rgba(14,165,233,0.18)',
    maxWidth: '88%',
  },
  userText: {
    color: theme.colors.text,
    fontSize: theme.typography.body,
    lineHeight: 23,
  },
})
