import React, { useEffect, useState } from 'react'
import { ActivityIndicator, StyleSheet, Text, View } from 'react-native'
import { ScreenScaffold } from './ScreenScaffold'
import { mobileApiClient } from '../api/mobileApi'
import { theme } from '../theme'

type LearningStatsPayload = {
  summary?: {
    learned_words?: number
    total_words?: number
    wrong_words?: number
  }
  alltime?: {
    learned_words?: number
    total_words?: number
    wrong_words?: number
  }
}

export function HomeScreen() {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [stats, setStats] = useState<LearningStatsPayload | null>(null)

  useEffect(() => {
    let active = true
    mobileApiClient
      .json<LearningStatsPayload>('/api/ai/learning-stats?days=7')
      .then(payload => {
        if (active) setStats(payload)
      })
      .catch(err => {
        if (active) setError(err instanceof Error ? err.message : '学习统计加载失败')
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [])

  const summary = stats?.summary ?? stats?.alltime

  return (
    <ScreenScaffold title="今日学习计划" subtitle="移动端 v1 聚焦学习者主链路。">
      <View style={styles.card}>
        {loading ? <ActivityIndicator color={theme.colors.primary} /> : null}
        {error ? <Text style={styles.error}>{error}</Text> : null}
        {!loading && !error ? (
          <>
            <Text style={styles.metric}>已学：{summary?.learned_words ?? 0}</Text>
            <Text style={styles.metric}>总词量：{summary?.total_words ?? 0}</Text>
            <Text style={styles.metric}>错词：{summary?.wrong_words ?? 0}</Text>
          </>
        ) : null}
      </View>
    </ScreenScaffold>
  )
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: theme.colors.card,
    borderColor: theme.colors.border,
    borderRadius: theme.radius.card,
    borderWidth: 1,
    padding: theme.spacing.lg,
  },
  error: {
    color: theme.colors.danger,
  },
  metric: {
    color: theme.colors.text,
    fontSize: theme.typography.body,
    marginBottom: theme.spacing.sm,
  },
})
