import React, { useEffect, useRef, useState } from 'react'
import { ChevronLeft, Search as SearchIcon } from 'lucide-react-native'
import { KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native'
import { stripHtml, type MobileWord } from '@ielts-vocab/app-core'
import { loadWordDetails, saveWordNote, searchWords } from '../api/learnerApi'
import { Body, Card, Field, Heading, Meta, PrimaryButton, StatusText } from '../components/primitives'
import { DecoratedEmptyState } from '../components/stickers'
import type { Navigate, NavigateOptions } from '../navigation/types'
import { theme } from '../theme'

export function SearchScreen({
  goBack,
  navigate,
  options,
}: {
  goBack?: () => void
  navigate: Navigate
  options?: NavigateOptions
}) {
  const [term, setTerm] = useState(options?.word ?? '')
  const [words, setWords] = useState<MobileWord[]>([])
  const [details, setDetails] = useState('')
  const [note, setNote] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [hasSearched, setHasSearched] = useState(false)
  const inputRef = useRef<TextInput>(null)

  function back() {
    if (goBack) {
      goBack()
      return
    }
    navigate('home')
  }

  async function submit(value = term) {
    if (!value.trim()) return
    setHasSearched(true)
    setLoading(true)
    setError('')
    try {
      const results = await searchWords(value)
      setWords(results)
      if (results.length === 1) await openDetails(results[0].word)
    } catch (err) {
      setError(err instanceof Error ? err.message : '查词失败')
    } finally {
      setLoading(false)
    }
  }

  async function openDetails(word: string) {
    const payload = await loadWordDetails(word)
    setDetails(stripHtml(JSON.stringify(payload)).slice(0, 1600))
  }

  useEffect(() => {
    inputRef.current?.focus()
    if (options?.word) void submit(options.word)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [options?.word])

  return (
    <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={styles.screen}>
      <View style={styles.topBar}>
        <Pressable accessibilityLabel="返回" accessibilityRole="button" onPress={back} style={styles.backButton}>
          <ChevronLeft color={theme.colors.text} size={24} strokeWidth={2.2} />
        </Pressable>
        <View style={styles.searchField}>
          <SearchIcon color={theme.colors.textTertiary} size={22} strokeWidth={2.2} />
          <TextInput
            autoCapitalize="none"
            autoFocus
            onChangeText={setTerm}
            onSubmitEditing={() => void submit()}
            placeholder="搜索单词、释义或笔记"
            placeholderTextColor={theme.colors.textTertiary}
            ref={inputRef}
            returnKeyType="search"
            style={styles.searchInput}
            value={term}
          />
        </View>
      </View>

      <ScrollView
        contentContainerStyle={styles.content}
        keyboardDismissMode="on-drag"
        keyboardShouldPersistTaps="handled"
        style={styles.scroll}
      >
        <StatusText error={error} loading={loading} />

        {words.map(word => (
          <Card key={word.word}>
            <Heading>{word.word}</Heading>
            <Meta>
              {word.phonetic} {word.pos}
            </Meta>
            <Body>{word.definition}</Body>
            <PrimaryButton label="查看详情" onPress={() => void openDetails(word.word).catch(err => setError(err.message))} />
          </Card>
        ))}

        {hasSearched && !loading && !error && !words.length ? (
          <DecoratedEmptyState
            description="换个词再试试，或者直接查看已保存的词条笔记。"
            sticker="ieltsPaper"
            title="没有找到结果"
          />
        ) : null}

        {details ? (
          <Card>
            <Heading>词条详情</Heading>
            <Meta>{details}</Meta>
            <Field value={note} onChangeText={setNote} placeholder="词条笔记" multiline />
            <PrimaryButton label="保存笔记" onPress={() => void saveWordNote(term, note).catch(err => setError(err.message))} />
          </Card>
        ) : null}
      </ScrollView>
    </KeyboardAvoidingView>
  )
}

const styles = StyleSheet.create({
  backButton: {
    alignItems: 'center',
    height: 48,
    justifyContent: 'center',
    width: 24,
  },
  content: {
    backgroundColor: theme.colors.background,
    paddingHorizontal: theme.spacing.lg,
    paddingBottom: 160,
    paddingTop: theme.spacing.lg,
  },
  emptyState: {
    alignItems: 'center',
    backgroundColor: theme.colors.surfaceElevated,
    borderColor: theme.colors.borderStrong,
    borderRadius: theme.radius.card,
    borderWidth: 1,
    marginBottom: theme.spacing.md,
    paddingHorizontal: theme.spacing.lg,
    paddingVertical: theme.spacing.xl,
  },
  emptyText: {
    color: theme.colors.muted,
    fontSize: theme.typography.label,
    lineHeight: 22,
    textAlign: 'center',
  },
  emptyTitle: {
    color: theme.colors.text,
    fontSize: theme.typography.title,
    fontWeight: '900',
    marginBottom: theme.spacing.xs,
  },
  screen: {
    backgroundColor: theme.colors.background,
    flex: 1,
  },
  scroll: {
    backgroundColor: theme.colors.background,
    flex: 1,
  },
  searchField: {
    alignItems: 'center',
    backgroundColor: theme.colors.surfaceElevated,
    borderColor: theme.colors.borderStrong,
    borderRadius: 18,
    borderWidth: 1,
    flex: 1,
    flexDirection: 'row',
    gap: theme.spacing.sm,
    height: 56,
    paddingHorizontal: theme.spacing.md,
  },
  searchInput: {
    color: theme.colors.text,
    flex: 1,
    fontSize: theme.typography.body,
    paddingVertical: 0,
  },
  topBar: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: 2,
    paddingLeft: theme.spacing.sm,
    paddingRight: theme.spacing.lg,
    paddingTop: theme.spacing.lg,
  },
})
