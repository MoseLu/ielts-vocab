import React, { useEffect, useMemo, useState } from 'react'
import {
  PRACTICE_MODE_LABELS,
  buildCsv,
  type MobileWrongWordDimensionFilter,
  type MobileWrongWordFilters,
  type PracticeMode,
  type WrongWord,
} from '@ielts-vocab/app-core'
import { clearWrongWord, createCustomBook, loadWrongWords } from '../api/learnerApi'
import { Body, Card, Field, Heading, Meta, PrimaryButton, Row, ScreenScroll, StatusText } from '../components/primitives'
import { DecoratedEmptyState } from '../components/stickers'
import type { Navigate } from '../navigation/types'

const DIMENSION_OPTIONS: Array<{ label: string; value: MobileWrongWordDimensionFilter }> = [
  { label: '全部维度', value: 'all' },
  { label: '会认', value: 'recognition' },
  { label: '会想', value: 'meaning' },
  { label: '听音', value: 'listening' },
  { label: '听写', value: 'dictation' },
  { label: '跟读', value: 'speaking' },
]

const MODE_OPTIONS: Array<{ label: string; value: PracticeMode | 'all' }> = [
  { label: '全部模式', value: 'all' },
  { label: PRACTICE_MODE_LABELS.quickmemory, value: 'quickmemory' },
  { label: PRACTICE_MODE_LABELS.meaning, value: 'meaning' },
  { label: PRACTICE_MODE_LABELS.listening, value: 'listening' },
  { label: PRACTICE_MODE_LABELS.dictation, value: 'dictation' },
  { label: PRACTICE_MODE_LABELS.follow, value: 'follow' },
]

export function ErrorsScreen({ navigate }: { navigate: Navigate }) {
  const [words, setWords] = useState<WrongWord[]>([])
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [dimension, setDimension] = useState<MobileWrongWordDimensionFilter>('all')
  const [reviewMode, setReviewMode] = useState<PracticeMode | 'all'>('all')
  const [search, setSearch] = useState('')
  const [csv, setCsv] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const wrongWordFilters = useMemo<MobileWrongWordFilters>(() => ({
    dimension,
    mode: reviewMode,
    scope: 'pending',
  }), [dimension, reviewMode])

  function refresh(term = search, filters = wrongWordFilters) {
    setLoading(true)
    loadWrongWords(term, filters)
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
  const selectedWordValues = selectedWords.map(item => item.word)

  return (
    <ScreenScroll hideHeader title="错词本" subtitle="筛选错词维度，手动选择后进入多轮恢复练习。">
      <StatusText error={error} loading={loading} />
      <Card>
        <Field value={search} onChangeText={setSearch} placeholder="搜索错词" testID="errors.search" />
        <Row>
          <PrimaryButton label="搜索" onPress={() => refresh(search, wrongWordFilters)} testID="errors.searchSubmit" />
          <PrimaryButton label="错词强化" onPress={() => navigate('practice', { mode: 'errors', wrongWordFilters })} testID="errors.practice" />
          <PrimaryButton
            disabled={selectedWords.length === 0}
            label="练习已选"
            onPress={() => navigate('practice', {
              mode: 'errors',
              selectedWrongWords: selectedWordValues,
              wrongWordFilters,
            })}
            testID="errors.practiceSelected"
          />
        </Row>
      </Card>
      <Card>
        <Heading>恢复维度</Heading>
        <Meta>当前筛选：{DIMENSION_OPTIONS.find(item => item.value === dimension)?.label} · {MODE_OPTIONS.find(item => item.value === reviewMode)?.label}</Meta>
        <Row>
          {DIMENSION_OPTIONS.map(item => (
            <PrimaryButton
              key={item.value}
              label={item.label}
              onPress={() => {
                setDimension(item.value)
                refresh(search, { ...wrongWordFilters, dimension: item.value })
              }}
              testID={`errors.dimension.${item.value}`}
              tone={item.value === dimension ? 'accent' : 'neutral'}
            />
          ))}
        </Row>
        <Row>
          {MODE_OPTIONS.map(item => (
            <PrimaryButton
              key={item.value}
              label={item.label}
              onPress={() => {
                setReviewMode(item.value)
                refresh(search, { ...wrongWordFilters, mode: item.value })
              }}
              testID={`errors.mode.${item.value}`}
              tone={item.value === reviewMode ? 'accent' : 'neutral'}
            />
          ))}
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
      {!loading && !words.length ? (
        <DecoratedEmptyState
          actionLabel="开始基础练习"
          description="错词清空是个好信号，可以继续做一轮基础训练巩固记忆。"
          onAction={() => navigate('practice', { mode: 'smart' })}
          sticker="wrongWordSticky"
          title="暂无错词"
        />
      ) : null}
    </ScreenScroll>
  )
}
