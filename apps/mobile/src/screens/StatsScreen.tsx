import React from 'react'
import { Text } from 'react-native'
import { ScreenScaffold } from './ScreenScaffold'

export function StatsScreen() {
  return (
    <ScreenScaffold title="学习统计" subtitle="移动端统计复用现有学习统计接口。">
      <Text>已学、错词、连续学习等指标将在这里展示。</Text>
    </ScreenScaffold>
  )
}
