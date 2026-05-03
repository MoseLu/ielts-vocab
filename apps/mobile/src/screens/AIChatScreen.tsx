import React from 'react'
import { Text } from 'react-native'
import { ScreenScaffold } from './ScreenScaffold'

export function AIChatScreen() {
  return (
    <ScreenScaffold title="AI 助手" subtitle="移动端入口先接入现有 AI 网关，后续补充语音输入。">
      <Text>AI 对话消息列表和输入框将在这里呈现。</Text>
    </ScreenScaffold>
  )
}
