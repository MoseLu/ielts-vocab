import React from 'react'
import { Pressable, Text, View } from 'react-native'
import type { PracticeMode } from '@ielts-vocab/app-core'
import { Pill } from '../components/primitives'
import type { PracticeEntryKey } from './PracticeEntryPanel'
import { entryLabel, scoreLabel } from './PracticeScreen.helpers'
import { styles } from './PracticeScreen.styles'

export function PracticeStatusHeader({
  chapterLabel,
  correctCount,
  entry,
  mode,
  onOpenMode,
  onOpenScope,
  progress,
  queueIndex,
  queueLength,
  selectedBookTitle,
  wrongCount,
}: {
  chapterLabel: string
  correctCount: number
  entry: PracticeEntryKey | null
  mode: PracticeMode
  onOpenMode: () => void
  onOpenScope: () => void
  progress: number
  queueIndex: number
  queueLength: number
  selectedBookTitle?: string
  wrongCount: number
}) {
  return (
    <>
      <View style={styles.practiceStatusBar}>
        <Pressable accessibilityLabel="切换练习词书" accessibilityRole="button" onPress={onOpenScope} style={styles.statusSegment} testID="practice.scope.book">
          <Text style={styles.statusLabel}>词书</Text>
          <Text numberOfLines={1} style={styles.statusValue}>{selectedBookTitle || '选择词书'}</Text>
        </Pressable>
        <Pressable accessibilityLabel="切换练习章节" accessibilityRole="button" onPress={onOpenScope} style={styles.statusSegment} testID="practice.scope.chapter">
          <Text style={styles.statusLabel}>章节</Text>
          <Text numberOfLines={1} style={styles.statusValue}>{chapterLabel}</Text>
        </Pressable>
        <Pressable accessibilityLabel="切换练习模式" accessibilityRole="button" onPress={onOpenMode} style={styles.statusSegment} testID="practice.mode.switch">
          <Text style={styles.statusLabel}>模式</Text>
          <Text numberOfLines={1} style={styles.statusValue}>{entryLabel(entry, mode)}</Text>
        </Pressable>
      </View>
      <View style={styles.progressMini}>
        <View style={styles.progressTrack}>
          <View style={[styles.progressFill, { width: `${progress}%` }]} />
        </View>
        <View style={styles.statRow}>
          <Pill label={`${queueIndex}/${queueLength || 0}`} />
          <Pill label={scoreLabel('对', correctCount)} />
          <Pill label={scoreLabel('错', wrongCount)} />
        </View>
      </View>
    </>
  )
}
