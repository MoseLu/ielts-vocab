import React, { useEffect, useState } from 'react'
import { Text } from 'react-native'
import { buildCsv, type WrongWord } from '@ielts-vocab/app-core'
import { clearWrongWord, createCustomBook, loadWrongWords } from '../api/learnerApi'
import { Body, Card, Field, Heading, Meta, PrimaryButton, Row, ScreenScroll, StatusText } from '../components/primitives'
import type { Navigate } from '../navigation/types'

export function ErrorsScreen({ navigate }: { navigate: Navigate }) {
  const [words, setWords] = useState<WrongWord[]>([])
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [search, setSearch] = useState('')
  const [csv, setCsv] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  function refresh(term = search) {
    setLoading(true)
    loadWrongWords(term)
      .then(setWords)
      .catch(err => setError(err instanceof Error ? err.message : '错词加载失败'))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    refresh('')
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  function toggle(word: string) {
    setSelected(prev => {
      const next = new Set(prev)
      if (next.has(word)) next.delete(word)
      else next.add(word)
      return next
    })
  }

  const selectedWords = words.filter(item => selected.has(item.word))

  return (
    <ScreenScroll hideHeader title="错词本" subtitle="搜索、清错、导出，并把错词保存为自定义词书。">
      <StatusText error={error} loading={loading} />
      <Card>
        <Field value={search} onChangeText={setSearch} placeholder="搜索错词" />
        <Row>
          <PrimaryButton label="搜索" onPress={() => refresh(search)} />
          <PrimaryButton label="错词强化" onPress={() => navigate('practice', { mode: 'errors' })} />
        </Row>
      </Card>
      <Card>
        <Heading>批量操作</Heading>
        <Meta>已选择 {selected.size} / {words.length}</Meta>
        <PrimaryButton
          label="导出 CSV 预览"
          onPress={() => setCsv(buildCsv((selectedWords.length ? selectedWords : words).map(item => ({
            word: item.word,
            definition: item.definition,
            phonetic: item.phonetic,
            pos: item.pos,
            wrong_count: item.wrong_count,
          }))))}
        />
        <PrimaryButton label="保存为自定义词书" onPress={() => void createCustomBook('移动端错词本', selectedWords.length ? selectedWords : words).catch(err => setError(err.message))} />
      </Card>
      {csv ? (
        <Card>
          <Heading>CSV</Heading>
          <Meta>{csv.slice(0, 1200)}</Meta>
        </Card>
      ) : null}
      {words.map(item => (
        <Card key={item.word}>
          <Heading>{item.word}</Heading>
          <Meta>{item.phonetic} {item.pos} · 错 {item.wrong_count ?? 1}</Meta>
          <Body>{item.definition}</Body>
          <Row>
            <PrimaryButton label={selected.has(item.word) ? '取消选择' : '选择'} tone="neutral" onPress={() => toggle(item.word)} />
            <PrimaryButton label="清错" tone="danger" onPress={() => void clearWrongWord(item.word).then(() => refresh()).catch(err => setError(err.message))} />
          </Row>
        </Card>
      ))}
      {!loading && !words.length ? <Text>暂无错词。</Text> : null}
    </ScreenScroll>
  )
}
