import React, { useEffect, useState } from 'react'
import { ActivityIndicator, FlatList, StyleSheet, Text, View } from 'react-native'
import { BookSummarySchema, type BookSummary } from '@ielts-vocab/app-core'
import { ScreenScaffold } from './ScreenScaffold'
import { mobileApiClient } from '../api/mobileApi'
import { theme } from '../theme'

type BooksPayload = {
  books?: unknown[]
}

export function BooksScreen() {
  const [books, setBooks] = useState<BookSummary[]>([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let active = true
    mobileApiClient
      .json<BooksPayload>('/api/books')
      .then(payload => {
        const parsedBooks = (payload.books ?? [])
          .map(book => BookSummarySchema.safeParse(book))
          .filter(result => result.success)
          .map(result => result.data)
        if (active) setBooks(parsedBooks)
      })
      .catch(err => {
        if (active) setError(err instanceof Error ? err.message : '词书加载失败')
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [])

  return (
    <ScreenScaffold title="词书" subtitle="后续接入 /api/books 与章节进度接口。">
      {loading ? <ActivityIndicator color={theme.colors.primary} /> : null}
      {error ? <Text style={styles.error}>{error}</Text> : null}
      <FlatList
        data={books}
        keyExtractor={item => String(item.id)}
        renderItem={({ item }) => (
          <View style={styles.bookCard}>
            <Text style={styles.bookTitle}>{item.title}</Text>
            <Text style={styles.bookMeta}>{item.level || item.category || 'IELTS'} · {item.total_words} words</Text>
            {item.description ? <Text style={styles.bookDescription}>{item.description}</Text> : null}
          </View>
        )}
      />
    </ScreenScaffold>
  )
}

const styles = StyleSheet.create({
  bookCard: {
    backgroundColor: theme.colors.card,
    borderColor: theme.colors.border,
    borderRadius: theme.radius.card,
    borderWidth: 1,
    marginBottom: theme.spacing.md,
    padding: theme.spacing.lg,
  },
  bookDescription: {
    color: theme.colors.muted,
    lineHeight: 20,
    marginTop: theme.spacing.sm,
  },
  bookMeta: {
    color: theme.colors.muted,
    marginTop: theme.spacing.xs,
  },
  bookTitle: {
    color: theme.colors.text,
    fontSize: theme.typography.title,
    fontWeight: '700',
  },
  error: {
    color: theme.colors.danger,
    marginBottom: theme.spacing.md,
  },
})
