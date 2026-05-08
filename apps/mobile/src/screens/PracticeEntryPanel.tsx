import React from 'react'
import { Pressable, Text, View } from 'react-native'
import type { PracticeMode } from '@ielts-vocab/app-core'
import { Card, Heading, Meta, PrimaryButton, Row } from '../components/primitives'
import {
  Sticker,
  StickerLayer,
  modeStickerKeys,
  practiceCompleteStickerSlots,
  practiceEntryStickerSlots,
} from '../components/stickers'
import { styles } from './PracticeScreen.styles'

export type PracticeEntryKey = 'ebbinghaus' | 'errors' | 'follow' | 'regular' | 'speaking'

export type PracticeEntry = {
  key: PracticeEntryKey
  label: string
  mode?: PracticeMode
  subtitle: string
  tags: string[]
}

type PracticeModeGroup = {
  entries: PracticeEntry[]
  key: string
  subtitle: string
  title: string
}

export const PRACTICE_GROUPS: PracticeModeGroup[] = [
  {
    entries: [
      { key: 'regular', label: '基础训练', mode: 'smart', subtitle: '速记、听力、释义、拼写', tags: ['smart', 'listening', 'dictation'] },
      { key: 'ebbinghaus', label: '艾宾浩斯复习', mode: 'quickmemory', subtitle: '按复习节奏巩固记忆', tags: ['quickmemory'] },
    ],
    key: 'foundation',
    subtitle: '直接服务词汇积累，不进入五维闯关。',
    title: '基础学习闭环',
  },
  {
    entries: [
      { key: 'errors', label: '错词恢复', mode: 'errors', subtitle: '集中处理历史错词', tags: ['errors'] },
      { key: 'follow', label: '听说专项', mode: 'follow', subtitle: '跟读、听音和拼写细节', tags: ['follow', 'listening'] },
    ],
    key: 'recovery',
    subtitle: '把弱项拆成可执行的小任务。',
    title: '弱项修复',
  },
  {
    entries: [
      { key: 'speaking', label: 'AI 口语进阶', subtitle: '进入真题口语评分', tags: ['speaking', 'exams'] },
    ],
    key: 'advanced',
    subtitle: '高级能力仍保持独立入口。',
    title: '进阶模式',
  },
]

export function PracticeEntryPanel({ onOpen }: { onOpen: (item: PracticeEntry) => void }) {
  return (
    <>
      <Card style={styles.practiceHero}>
        <StickerLayer slots={practiceEntryStickerSlots} />
        <Text style={styles.practiceHeroEyebrow}>Practice System</Text>
        <Heading>今天先选一个学习动作</Heading>
        <Meta>基础训练、艾宾浩斯、错词恢复和听说专项都在这里；五维闯关仍保持独立高级入口。</Meta>
      </Card>
      {PRACTICE_GROUPS.map(group => (
        <View key={group.key} style={styles.entryGroup}>
          <View style={styles.entryGroupHeader}>
            <Text style={styles.entryGroupTitle}>{group.title}</Text>
            <Text style={styles.entryGroupSubtitle}>{group.subtitle}</Text>
          </View>
          <View style={styles.entryGrid}>
            {group.entries.map(item => (
              <Pressable key={item.key} accessibilityRole="button" onPress={() => onOpen(item)} style={styles.entryTile}>
                <Sticker height={68} keyName={modeStickerKeys[item.key]} width={68} />
                <Text style={styles.entryTitle}>{item.label}</Text>
                <Text numberOfLines={2} style={styles.entrySubtitle}>{item.subtitle}</Text>
                <View style={styles.entryTags}>
                  {item.tags.map(tag => (
                    <Text key={tag} style={styles.entryTag}>{tag}</Text>
                  ))}
                </View>
              </Pressable>
            ))}
          </View>
        </View>
      ))}
    </>
  )
}

export function PracticeCompletionCard({
  onChangeScope,
  onRestart,
  wordCount,
}: {
  onChangeScope: () => void
  onRestart: () => void
  wordCount: number
}) {
  return (
    <Card style={styles.completedCard}>
      <StickerLayer slots={practiceCompleteStickerSlots} />
      <Heading>本轮完成</Heading>
      <Meta>{wordCount} 个词已过一遍，可从顶部状态栏切换模式或范围。</Meta>
      <Row>
        <PrimaryButton label="再来一轮" onPress={onRestart} />
        <PrimaryButton label="换范围" tone="neutral" onPress={onChangeScope} />
      </Row>
    </Card>
  )
}
