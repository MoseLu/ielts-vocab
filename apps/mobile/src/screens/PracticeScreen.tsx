import React, { useRef, useState } from 'react'
import { Pressable, StyleSheet, Text, View } from 'react-native'
import { ScreenScaffold } from './ScreenScaffold'
import { useMobileSpeechRecognition } from '../speech/useMobileSpeechRecognition'
import { theme } from '../theme'

export function PracticeScreen() {
  const { start, state: speechState, stop } = useMobileSpeechRecognition('en')
  const [error, setError] = useState('')
  const cleanupRef = useRef<(() => void) | null>(null)

  async function toggleRecording() {
    if (speechState.status === 'recording') {
      cleanupRef.current?.()
      cleanupRef.current = null
      await stop()
      return
    }
    setError('')
    try {
      cleanupRef.current = await start()
    } catch (err) {
      setError(err instanceof Error ? err.message : '无法开始录音')
    }
  }

  return (
    <ScreenScaffold title="跟读练习" subtitle="原生录音模块输出 PCM16，服务端 ASR 返回实时识别结果。">
      <View style={styles.panel}>
        <Text style={styles.label}>状态：{speechState.status}</Text>
        <Text style={styles.label}>音量：{Math.round(speechState.level * 100)}%</Text>
        <Text style={styles.transcript}>{speechState.finalText || speechState.partialText || '等待录音'}</Text>
        {speechState.error || error ? <Text style={styles.error}>{speechState.error || error}</Text> : null}
      </View>
      <Pressable onPress={toggleRecording} style={styles.button}>
        <Text style={styles.buttonText}>{speechState.status === 'recording' ? '停止录音' : '开始录音'}</Text>
      </Pressable>
    </ScreenScaffold>
  )
}

const styles = StyleSheet.create({
  button: {
    alignItems: 'center',
    backgroundColor: theme.colors.primary,
    borderRadius: theme.radius.control,
    height: 48,
    justifyContent: 'center',
    marginTop: theme.spacing.lg,
  },
  buttonText: {
    color: theme.colors.textInverse,
    fontWeight: '700',
  },
  label: {
    color: theme.colors.muted,
    marginBottom: theme.spacing.sm,
  },
  error: {
    color: theme.colors.danger,
    marginTop: theme.spacing.md,
  },
  panel: {
    backgroundColor: theme.colors.card,
    borderColor: theme.colors.border,
    borderRadius: theme.radius.card,
    borderWidth: 1,
    padding: theme.spacing.lg,
  },
  transcript: {
    color: theme.colors.text,
    fontSize: theme.typography.title,
    fontWeight: '700',
    marginTop: theme.spacing.md,
  },
})
