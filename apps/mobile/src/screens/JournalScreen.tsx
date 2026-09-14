import React, { useEffect, useState } from 'react'
import {
  loadJournalSummaries,
  loadLearningNotes,
  loadTodayJournalEntry,
  saveTodayJournalEntry,
  startSummaryJob,
} from '../api/learnerApi'
import { Body, Card, Field, Heading, Meta, PrimaryButton, ScreenScroll, StatusText } from '../components/primitives'
import type { JournalSummary, LearningNote } from '@ielts-vocab/app-core'

function today() {
  return new Date().toISOString().slice(0, 10)
}

export function JournalScreen() {
  const [summaries, setSummaries] = useState<JournalSummary[]>([])
  const [notes, setNotes] = useState<LearningNote[]>([])
  const [recapDraft, setRecapDraft] = useState('')
  const [date, setDate] = useState(today())
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  function refresh() {
    setLoading(true)
    Promise.all([loadJournalSummaries(), loadLearningNotes(), loadTodayJournalEntry()])
      .then(([nextSummaries, nextNotes, todayEntry]) => {
        setSummaries(nextSummaries)
        setNotes(nextNotes)
        setRecapDraft(todayEntry?.content ?? '')
      })
      .catch(err => setError(err instanceof Error ? err.message : '日志加载失败'))
      .finally(() => setLoading(false))
  }

  useEffect(refresh, [])

  async function generate() {
    setNotice('')
    const payload = await startSummaryJob(date)
    setNotice(`总结任务已提交：${JSON.stringify(payload).slice(0, 160)}`)
  }

  async function saveRecap() {
    setNotice('')
    const entry = await saveTodayJournalEntry(recapDraft)
    setRecapDraft(entry.content ?? '')
    setNotice('今日复盘已保存')
  }

  return (
    <ScreenScroll hideHeader title="学习日志" subtitle="今日复盘、每日总结和问答历史在移动端可查看与触发生成。">
      <StatusText error={error} loading={loading} />
      {notice ? <Meta>{notice}</Meta> : null}
      <Card>
        <Heading>今日复盘</Heading>
        <Body>写下今天完成了什么、进度如何、查漏补缺和下一步。</Body>
        <Field
          multiline
          value={recapDraft}
          onChangeText={setRecapDraft}
          placeholder="今天完成了什么？进度如何？哪里需要补？下一步做什么？"
          testID="journal.recap"
        />
        <PrimaryButton
          label="保存今日复盘"
          onPress={() => void saveRecap().catch(err => setError(err.message))}
          testID="journal.recap.save"
        />
      </Card>
      <Card>
        <Heading>生成 AI 总结</Heading>
        <Field value={date} onChangeText={setDate} placeholder="YYYY-MM-DD" testID="journal.date" />
        <PrimaryButton label="生成总结" onPress={() => void generate().then(refresh).catch(err => setError(err.message))} testID="journal.generate" />
      </Card>
      {summaries.map(summary => (
        <Card key={String(summary.id ?? summary.date)}>
          <Heading>{summary.title || summary.date || '每日总结'}</Heading>
          <Meta>{summary.created_at}</Meta>
          <Body>{summary.content || summary.markdown || summary.summary || '暂无内容'}</Body>
        </Card>
      ))}
      {notes.map(note => (
        <Card key={String(note.id ?? note.created_at)}>
          <Heading>{note.question || note.word || '问答记录'}</Heading>
          <Meta>{note.created_at}</Meta>
          <Body>{note.answer || note.content || '暂无内容'}</Body>
        </Card>
      ))}
    </ScreenScroll>
  )
}
