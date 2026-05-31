import React, { useEffect, useState } from 'react'
import { loadJournalSummaries, loadLearningNotes, startSummaryJob } from '../api/learnerApi'
import { Body, Card, Field, Heading, Meta, PrimaryButton, ScreenScroll, StatusText } from '../components/primitives'
import type { JournalSummary, LearningNote } from '@ielts-vocab/app-core'

function today() {
  return new Date().toISOString().slice(0, 10)
}

export function JournalScreen() {
  const [summaries, setSummaries] = useState<JournalSummary[]>([])
  const [notes, setNotes] = useState<LearningNote[]>([])
  const [date, setDate] = useState(today())
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  function refresh() {
    setLoading(true)
    Promise.all([loadJournalSummaries(), loadLearningNotes()])
      .then(([nextSummaries, nextNotes]) => {
        setSummaries(nextSummaries)
        setNotes(nextNotes)
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

  return (
    <ScreenScroll hideHeader title="学习日志" subtitle="每日总结、问答历史和导出内容在移动端可查看与触发生成。">
      <StatusText error={error} loading={loading} />
      {notice ? <Meta>{notice}</Meta> : null}
      <Card>
        <Heading>生成今日总结</Heading>
        <Field value={date} onChangeText={setDate} placeholder="YYYY-MM-DD" />
        <PrimaryButton label="生成总结" onPress={() => void generate().then(refresh).catch(err => setError(err.message))} />
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
