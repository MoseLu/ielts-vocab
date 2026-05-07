import React, { useEffect, useState } from 'react'
import { Text } from 'react-native'
import { loadLearnerProfile, loadLearningStats } from '../api/learnerApi'
import { Card, Heading, Meta, Pill, PrimaryButton, Row, ScreenScroll, StatusText } from '../components/primitives'
import type { Navigate } from '../navigation/types'

function metric(source: Record<string, unknown> | undefined, key: string): string {
  const value = source?.[key]
  return typeof value === 'number' || typeof value === 'string' ? String(value) : '0'
}

export function StatsScreen({ navigate }: { navigate: Navigate }) {
  const [stats, setStats] = useState<Record<string, unknown>>({})
  const [profile, setProfile] = useState<Record<string, unknown>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([loadLearningStats(), loadLearnerProfile()])
      .then(([nextStats, nextProfile]) => {
        setStats(nextStats.summary ?? nextStats.alltime)
        setProfile(nextProfile)
      })
      .catch(err => setError(err instanceof Error ? err.message : '统计加载失败'))
      .finally(() => setLoading(false))
  }, [])

  return (
    <ScreenScroll hideHeader title="学习统计" subtitle="学习概览、错词趋势、模式表现和画像建议。">
      <StatusText error={error} loading={loading} />
      <Card>
        <Heading>概览</Heading>
        <Row>
          <Pill label={`已学 ${metric(stats, 'learned_words')}`} />
          <Pill label={`总词 ${metric(stats, 'total_words')}`} />
          <Pill label={`错词 ${metric(stats, 'wrong_words')}`} />
          <Pill label={`连续 ${metric(stats, 'streak_days')} 天`} />
        </Row>
      </Card>
      <Card>
        <Heading>学习者画像</Heading>
        <Meta>{JSON.stringify(profile).slice(0, 1200) || '暂无画像数据'}</Meta>
      </Card>
      <Card>
        <Heading>复习动作</Heading>
        <PrimaryButton label="到期复习" onPress={() => navigate('practice', { mode: 'quickmemory' })} />
        <PrimaryButton label="错词本" onPress={() => navigate('errors')} />
      </Card>
      {!loading && !Object.keys(stats).length ? <Text>暂无统计数据。</Text> : null}
    </ScreenScroll>
  )
}
