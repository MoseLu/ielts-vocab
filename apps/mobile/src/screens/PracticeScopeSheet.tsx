import React from 'react'
import { Modal, Pressable, ScrollView, Text, View } from 'react-native'
import { ChevronRight } from 'lucide-react-native'
import { PRACTICE_MODE_LABELS, type MobileBook, type MobileChapter, type PracticeMode } from '@ielts-vocab/app-core'
import { Field } from '../components/primitives'
import { StickerLayer, practiceSheetStickerSlots } from '../components/stickers'
import { theme } from '../theme'
import { PRACTICE_MODE_HINTS, PRACTICE_MODES } from './PracticeScreen.helpers'
import { styles } from './PracticeScreen.styles'

type PracticeScopeSheetProps = {
  bookId: string
  chapterId: string | number | null
  filteredBooks: MobileBook[]
  filteredChapters: MobileChapter[]
  mode: PracticeMode
  onChooseChapter: (chapter: MobileChapter | null) => void
  onChooseMode: (mode: PracticeMode) => void
  onClose: () => void
  onSelectBook: (bookId: string) => void
  scopeQuery: string
  setScopeQuery: (value: string) => void
  sheet: 'mode' | 'scope' | null
}

export function PracticeScopeSheet({
  bookId,
  chapterId,
  filteredBooks,
  filteredChapters,
  mode,
  onChooseChapter,
  onChooseMode,
  onClose,
  onSelectBook,
  scopeQuery,
  setScopeQuery,
  sheet,
}: PracticeScopeSheetProps) {
  return (
    <Modal animationType="slide" onRequestClose={onClose} transparent visible={sheet !== null}>
      <View style={styles.sheetRoot}>
        <Pressable accessibilityRole="button" onPress={onClose} style={styles.sheetBackdrop} />
        <View style={styles.sheetPanel}>
          <StickerLayer slots={practiceSheetStickerSlots} />
          <View style={styles.sheetGrabber} />
          {sheet === 'mode' ? (
            <>
              <Text style={styles.sheetTitle}>切换练习模式</Text>
              <Text style={styles.sheetSubtitle}>沿用当前范围，切换后直接重新出题。</Text>
              <ScrollView keyboardShouldPersistTaps="handled" showsVerticalScrollIndicator={false} style={styles.sheetScroll} contentContainerStyle={styles.sheetScrollContent}>
                {PRACTICE_MODES.map(item => {
                  const active = item === mode
                  return (
                    <Pressable key={item} accessibilityLabel={`练习模式-${PRACTICE_MODE_LABELS[item]}`} accessibilityRole="button" onPress={() => onChooseMode(item)} style={[styles.sheetRow, active ? styles.sheetRowActive : null]} testID={`practice.mode.${item}`}>
                      <View style={styles.sheetIcon}>
                        <Text style={styles.sheetIndex}>{PRACTICE_MODE_LABELS[item].slice(0, 1)}</Text>
                      </View>
                      <View style={styles.sheetBody}>
                        <Text style={styles.sheetLabel}>{PRACTICE_MODE_LABELS[item]}</Text>
                        <Text style={styles.sheetMeta}>{PRACTICE_MODE_HINTS[item]}</Text>
                      </View>
                      <ChevronRight color={theme.colors.textTertiary} size={18} />
                    </Pressable>
                  )
                })}
              </ScrollView>
            </>
          ) : (
            <>
              <Text style={styles.sheetTitle}>选择练习范围</Text>
              <Text style={styles.sheetSubtitle}>搜索词书或章节，章节为空时默认按整本词书出题。</Text>
              <Field value={scopeQuery} onChangeText={setScopeQuery} placeholder="搜索当前词书或章节" />
              <ScrollView keyboardShouldPersistTaps="handled" showsVerticalScrollIndicator={false} style={styles.sheetScroll} contentContainerStyle={styles.sheetScrollContent}>
                <Text style={styles.sheetGroup}>词书</Text>
                {filteredBooks.map(book => {
                  const active = String(book.id) === bookId
                  return (
                    <Pressable key={String(book.id)} accessibilityLabel={`选择练习词书-${book.title}`} accessibilityRole="button" onPress={() => onSelectBook(String(book.id))} style={[styles.sheetRow, active ? styles.sheetRowActive : null]} testID={`practice.scope.book.${String(book.id)}`}>
                      <View style={styles.sheetBody}>
                        <Text numberOfLines={1} style={styles.sheetLabel}>{book.title}</Text>
                        <Text style={styles.sheetMeta}>{book.total_words || book.word_count || 0} 词</Text>
                      </View>
                      <ChevronRight color={theme.colors.textTertiary} size={18} />
                    </Pressable>
                  )
                })}
                {bookId ? <Text style={styles.sheetGroup}>章节</Text> : null}
                {bookId ? (
                  <Pressable accessibilityLabel="选择整本词书" accessibilityRole="button" onPress={() => onChooseChapter(null)} style={[styles.sheetRow, chapterId == null ? styles.sheetRowActive : null]} testID="practice.scope.wholeBook">
                    <View style={styles.sheetIcon}>
                      <Text style={styles.sheetIndex}>全</Text>
                    </View>
                    <View style={styles.sheetBody}>
                      <Text style={styles.sheetLabel}>整本词书</Text>
                      <Text style={styles.sheetMeta}>不限定章节，按当前词书生成队列。</Text>
                    </View>
                    <ChevronRight color={theme.colors.textTertiary} size={18} />
                  </Pressable>
                ) : null}
                {filteredChapters.map((chapter, idx) => (
                  <Pressable key={String(chapter.id)} accessibilityLabel={`选择练习章节-${chapter.title}`} accessibilityRole="button" onPress={() => onChooseChapter(chapter)} style={[styles.sheetRow, String(chapter.id) === String(chapterId) ? styles.sheetRowActive : null]} testID={`practice.scope.chapter.${String(chapter.id)}`}>
                    <View style={styles.sheetIcon}>
                      <Text style={styles.sheetIndex}>{String(idx + 1).padStart(2, '0')}</Text>
                    </View>
                    <View style={styles.sheetBody}>
                      <Text numberOfLines={1} style={styles.sheetLabel}>{chapter.title}</Text>
                      <Text style={styles.sheetMeta}>{chapter.word_count || chapter.group_count || 0} 项</Text>
                    </View>
                    <ChevronRight color={theme.colors.textTertiary} size={18} />
                  </Pressable>
                ))}
              </ScrollView>
            </>
          )}
        </View>
      </View>
    </Modal>
  )
}
