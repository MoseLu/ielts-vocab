import React, { useMemo, useState } from 'react'
import { StyleSheet, Text, View } from 'react-native'
import type { MobileWord } from '@ielts-vocab/app-core'
import { createCustomBook } from '../api/learnerApi'
import { Body, Card, Field, Heading, Meta, PrimaryButton, Row, ScreenScroll, StatusText } from '../components/primitives'
import type { Navigate } from '../navigation/types'
import { theme } from '../theme'

function makeCustomWord(line: string): MobileWord | null {
  const [rawWord, definition = '', phonetic = '', pos = ''] = line.split(/[,，\t]/)
  const word = rawWord?.trim()
  if (!word) return null
  return {
    word,
    definition: definition.trim(),
    phonetic: phonetic.trim(),
    pos: pos.trim(),
    group_key: '',
    book_id: '',
    book_title: '',
    chapter_id: '',
    chapter_title: '',
    examples: [],
    listening_confusables: [],
  }
}

export function CustomBookScreen({
  goBack,
  navigate,
}: {
  goBack?: () => void
  navigate: Navigate
}) {
  const [title, setTitle] = useState('')
  const [wordsText, setWordsText] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const words = useMemo(
    () => wordsText.split(/\n+/).map(line => makeCustomWord(line.trim())).filter((word): word is MobileWord => Boolean(word)),
    [wordsText],
  )

  async function save() {
    if (!title.trim() || !words.length) {
      setError('请填写词书名称，并至少添加一个词条')
      return
    }
    setLoading(true)
    setError('')
    try {
      await createCustomBook(title.trim(), words)
      navigate('books')
    } catch (err) {
      setError(err instanceof Error ? err.message : '自定义词书保存失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <ScreenScroll hideHeader title="自定义词书" subtitle="创建一本可直接进入章节学习的词书。">
      <StatusText error={error} loading={loading} />
      <Card style={styles.hero}>
        <Meta>自定义词书</Meta>
        <Heading>创建一本可立即学习的词书</Heading>
        <Body>词书会保存到“我的词书”，返回词书页后可进入章节和基础练习。</Body>
      </Card>
      <Card>
        <Field value={title} onChangeText={setTitle} placeholder="词书名称" />
        <Field
          multiline
          value={wordsText}
          onChangeText={setWordsText}
          placeholder="每行一个词：word,中文释义,音标,词性"
          style={styles.wordsInput}
        />
        <View style={styles.previewHead}>
          <Meta>已识别 {words.length} 个词条</Meta>
          <Text style={styles.hint}>逗号或制表符分隔</Text>
        </View>
        {words.slice(0, 4).map(word => (
          <View key={word.word} style={styles.wordRow}>
            <Text style={styles.word}>{word.word}</Text>
            <Text numberOfLines={1} style={styles.definition}>{word.definition || '暂无释义'}</Text>
          </View>
        ))}
        <Row>
          <PrimaryButton label="保存词书" onPress={() => void save()} />
          <PrimaryButton label="取消" tone="neutral" onPress={() => (goBack ? goBack() : navigate('books'))} />
        </Row>
      </Card>
    </ScreenScroll>
  )
}

const styles = StyleSheet.create({
  definition: {
    color: theme.colors.muted,
    flex: 1,
    fontSize: theme.typography.label,
  },
  hero: {
    backgroundColor: theme.colors.surface,
  },
  hint: {
    color: theme.colors.textTertiary,
    fontSize: theme.typography.caption,
    fontWeight: '700',
  },
  previewHead: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: theme.spacing.sm,
  },
  word: {
    color: theme.colors.text,
    fontSize: theme.typography.label,
    fontWeight: '900',
    width: 112,
  },
  wordRow: {
    borderBottomColor: theme.colors.border,
    borderBottomWidth: 1,
    flexDirection: 'row',
    gap: theme.spacing.md,
    paddingVertical: theme.spacing.sm,
  },
  wordsInput: {
    minHeight: 172,
    paddingTop: theme.spacing.md,
    textAlignVertical: 'top',
  },
})
