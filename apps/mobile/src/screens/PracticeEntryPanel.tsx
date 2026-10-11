import React from 'react'
import { ChevronRight } from 'lucide-react-native'
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

const PRACTICE_ENTRY_SHORTCUTS = PRACTICE_GROUPS.flatMap(group => group.entries)

export function PracticeEntryPanel({ onOpen }: { onOpen: (item: PracticeEntry) => void }) {
  return (
    <>
      <Card style={styles.practiceHero}>
        <StickerLayer slots={practiceEntryStickerSlots} />
        <Text style={styles.practiceHeroEyebrow}>练习中心</Text>
        <Heading>选择一个练习模式</Heading>
        <Meta>底部快捷菜单可直接进入常用练习，这里保留完整模式和范围切换。</Meta>
        <View style={styles.modeShortcutRail}>
          {PRACTICE_ENTRY_SHORTCUTS.map(item => (
            <Pressable
              accessibilityLabel={`快捷练习-${item.label}`}
              accessibilityRole="button"
              key={item.key}
              onPress={() => onOpen(item)}
              style={({ pressed }) => [styles.modeShortcut, pressed ? styles.modeShortcutPressed : null]}
              testID={`practice.modeShortcut.${item.key}`}
            >
              <View style={styles.modeShortcutIcon}>
                <Sticker height={46} keyName={modeStickerKeys[item.key]} width={46} />
              </View>
              <Text numberOfLines={1} style={styles.modeShortcutLabel}>{item.label}</Text>
            </Pressable>
          ))}
        </View>
      </Card>
      {PRACTICE_GROUPS.map(group => (
        <View key={group.key} style={styles.entryGroup}>
          <View style={styles.entryGroupHeader}>
            <Text style={styles.entryGroupTitle}>{group.title}</Text>
            <Text numberOfLines={1} style={styles.entryGroupSubtitle}>{group.subtitle}</Text>
          </View>
          <View style={styles.entryGrid}>
            {group.entries.map(item => (
              <Pressable
                accessibilityLabel={`练习入口-${item.label}`}
                accessibilityRole="button"
                key={item.key}
                onPress={() => onOpen(item)}
                style={({ pressed }) => [styles.entryTile, pressed ? styles.entryTilePressed : null]}
                testID={`practice.entry.${item.key}`}
              >
                <Sticker height={52} keyName={modeStickerKeys[item.key]} width={52} />
                <View style={styles.entryCopy}>
                  <Text style={styles.entryTitle}>{item.label}</Text>
                  <Text numberOfLines={1} style={styles.entrySubtitle}>{item.subtitle}</Text>
                  <View style={styles.entryTags}>
                    {item.tags.slice(0, 2).map(tag => (
                      <Text key={tag} style={styles.entryTag}>{tag}</Text>
                    ))}
                  </View>
                </View>
                <ChevronRight color="#A49286" size={18} strokeWidth={2.4} />
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
        <PrimaryButton label="再来一轮" onPress={onRestart} testID="practice.restart" />
        <PrimaryButton label="换范围" tone="neutral" onPress={onChangeScope} testID="practice.changeScope" />
      </Row>
    </Card>
  )
}
