import React, { useMemo, useState } from 'react'
import { Modal, Pressable, ScrollView, Text, View } from 'react-native'
import { Heart, List, Settings, SlidersHorizontal, Volume2 } from 'lucide-react-native'
import { PRACTICE_MODE_LABELS, type MobileWord, type PracticeMode } from '@ielts-vocab/app-core'
import { setFavorite } from '../api/learnerApi'
import { theme } from '../theme'
import { styles } from './PracticeScreen.styles'

type PracticeControlPanel = 'wordList' | 'settings' | null

function wordKey(word?: MobileWord | null) {
  return (word?.word ?? '').trim().toLowerCase()
}

export function PracticeControlSurface({
  activeMode,
  chapterLabel,
  currentWord,
  mode,
  onOpenMode,
  onOpenScope,
  onPlayWord,
  onRestart,
  onSelectWord,
  onSetFeedback,
  queue,
  queueIndex,
}: {
  activeMode: PracticeMode
  chapterLabel: string
  currentWord?: MobileWord
  mode: PracticeMode
  onOpenMode: () => void
  onOpenScope: () => void
  onPlayWord: () => void
  onRestart: () => void
  onSelectWord: (index: number) => void
  onSetFeedback: (message: string) => void
  queue: MobileWord[]
  queueIndex: number
}) {
  const [panel, setPanel] = useState<PracticeControlPanel>(null)
  const [favoriteWords, setFavoriteWords] = useState<Set<string>>(() => new Set())
  const [favoritePending, setFavoritePending] = useState(false)
  const currentWordKey = wordKey(currentWord)
  const favoriteActive = currentWordKey ? favoriteWords.has(currentWordKey) : false
  const canUseWordActions = Boolean(currentWord)
  const queueSummary = useMemo(() => {
    if (!queue.length) return '暂无队列'
    return `${Math.min(queueIndex + 1, queue.length)}/${queue.length} · ${chapterLabel}`
  }, [chapterLabel, queue.length, queueIndex])

  async function toggleFavorite() {
    if (!currentWord || favoritePending) return
    const key = wordKey(currentWord)
    if (!key) return
    const nextActive = !favoriteWords.has(key)
    setFavoritePending(true)
    setFavoriteWords(previous => {
      const next = new Set(previous)
      if (nextActive) next.add(key)
      else next.delete(key)
      return next
    })
    try {
      await setFavorite(currentWord.word, nextActive)
      onSetFeedback(nextActive ? '已加入收藏词书' : '已移出收藏词书')
    } catch (err) {
      setFavoriteWords(previous => {
        const next = new Set(previous)
        if (nextActive) next.delete(key)
        else next.add(key)
        return next
      })
      onSetFeedback(err instanceof Error ? err.message : '收藏更新失败')
    } finally {
      setFavoritePending(false)
    }
  }

  function pickWord(nextIndex: number) {
    onSelectWord(nextIndex)
    setPanel(null)
    onSetFeedback(`已切换到 ${queue[nextIndex]?.word ?? '目标词'}`)
  }

  return (
    <>
      <View style={styles.mobileControlSurface} testID="practice.controlSurface">
        <Pressable accessibilityLabel="切换练习范围" accessibilityRole="button" onPress={onOpenScope} style={styles.mobileControlPrimary} testID="practice.control.scope">
          <SlidersHorizontal color={theme.colors.primaryDark} size={18} />
          <View style={styles.mobileControlCopy}>
            <Text style={styles.mobileControlLabel}>范围</Text>
            <Text numberOfLines={1} style={styles.mobileControlValue}>{queueSummary}</Text>
          </View>
        </Pressable>
        <Pressable accessibilityLabel="切换练习模式" accessibilityRole="button" onPress={onOpenMode} style={styles.mobileControlPrimary} testID="practice.control.mode">
          <Text style={styles.mobileControlIconText}>{PRACTICE_MODE_LABELS[mode].slice(0, 1)}</Text>
          <View style={styles.mobileControlCopy}>
            <Text style={styles.mobileControlLabel}>模式</Text>
            <Text numberOfLines={1} style={styles.mobileControlValue}>{PRACTICE_MODE_LABELS[mode]}</Text>
          </View>
        </Pressable>
        <View style={styles.mobileControlActionRow}>
          <Pressable accessibilityLabel="打开单词列表" accessibilityRole="button" onPress={() => setPanel('wordList')} style={styles.mobileControlIconButton} testID="practice.control.wordList">
            <List color={theme.colors.text} size={18} />
            <Text style={styles.mobileControlTinyText}>列表</Text>
          </Pressable>
          <Pressable accessibilityLabel={favoriteActive ? '移出收藏词书' : '收藏当前单词'} accessibilityRole="button" accessibilityState={{ disabled: !canUseWordActions, selected: favoriteActive }} disabled={!canUseWordActions || favoritePending} onPress={() => void toggleFavorite()} style={[styles.mobileControlIconButton, favoriteActive ? styles.mobileControlIconButtonActive : null, !canUseWordActions ? styles.mobileControlIconButtonDisabled : null]} testID="practice.control.favorite">
            <Heart color={favoriteActive ? theme.colors.rose : theme.colors.text} fill={favoriteActive ? theme.colors.rose : 'none'} size={18} />
            <Text style={styles.mobileControlTinyText}>{favoritePending ? '更新' : '收藏'}</Text>
          </Pressable>
          <Pressable accessibilityLabel="播放当前单词发音" accessibilityRole="button" accessibilityState={{ disabled: !canUseWordActions }} disabled={!canUseWordActions} onPress={onPlayWord} style={[styles.mobileControlIconButton, !canUseWordActions ? styles.mobileControlIconButtonDisabled : null]} testID="practice.control.pronunciation">
            <Volume2 color={theme.colors.text} size={18} />
            <Text style={styles.mobileControlTinyText}>发音</Text>
          </Pressable>
          <Pressable accessibilityLabel="打开练习设置" accessibilityRole="button" onPress={() => setPanel('settings')} style={styles.mobileControlIconButton} testID="practice.control.settings">
            <Settings color={theme.colors.text} size={18} />
            <Text style={styles.mobileControlTinyText}>设置</Text>
          </Pressable>
        </View>
      </View>
      <Modal animationType="slide" onRequestClose={() => setPanel(null)} transparent visible={panel !== null}>
        <View style={styles.sheetRoot}>
          <Pressable accessibilityRole="button" onPress={() => setPanel(null)} style={styles.sheetBackdrop} />
          <View style={styles.sheetPanel}>
            <View style={styles.sheetGrabber} />
            {panel === 'wordList' ? (
              <>
                <Text style={styles.sheetTitle}>单词列表</Text>
                <Text style={styles.sheetSubtitle}>点击任意词条可跳转到对应练习位置。</Text>
                <ScrollView showsVerticalScrollIndicator={false} style={styles.sheetScroll} contentContainerStyle={styles.sheetScrollContent}>
                  {queue.map((word, itemIndex) => (
                    <Pressable key={`${word.word}-${itemIndex}`} accessibilityLabel={`切换到单词-${word.word}`} accessibilityRole="button" onPress={() => pickWord(itemIndex)} style={[styles.practiceWordListRow, itemIndex === queueIndex ? styles.practiceWordListRowActive : null]} testID={`practice.wordList.item.${itemIndex}`}>
                      <Text style={styles.practiceWordListIndex}>{String(itemIndex + 1).padStart(2, '0')}</Text>
                      <View style={styles.sheetBody}>
                        <Text numberOfLines={1} style={styles.sheetLabel}>{word.word}</Text>
                        <Text numberOfLines={2} style={styles.sheetMeta}>{[word.phonetic, word.definition].filter(Boolean).join(' · ')}</Text>
                      </View>
                    </Pressable>
                  ))}
                </ScrollView>
              </>
            ) : (
              <>
                <Text style={styles.sheetTitle}>练习设置</Text>
                <Text style={styles.sheetSubtitle}>当前模式：{PRACTICE_MODE_LABELS[mode]}，实际出题：{PRACTICE_MODE_LABELS[activeMode]}。</Text>
                <Pressable accessibilityRole="button" onPress={() => { setPanel(null); onOpenMode() }} style={styles.sheetRow} testID="practice.settings.mode">
                  <Text style={styles.sheetLabel}>切换模式</Text>
                </Pressable>
                <Pressable accessibilityRole="button" onPress={() => { setPanel(null); onOpenScope() }} style={styles.sheetRow} testID="practice.settings.scope">
                  <Text style={styles.sheetLabel}>切换范围</Text>
                </Pressable>
                <Pressable accessibilityRole="button" onPress={() => { setPanel(null); onRestart() }} style={styles.sheetRow} testID="practice.settings.restart">
                  <Text style={styles.sheetLabel}>重开本轮</Text>
                </Pressable>
              </>
            )}
          </View>
        </View>
      </Modal>
    </>
  )
}
