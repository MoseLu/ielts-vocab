import React, { useEffect, useState } from 'react'
import { Text } from 'react-native'
import { stripHtml, type ExamPaperDetail, type ExamPaperSummary, type ExamQuestion } from '@ielts-vocab/app-core'
import { createExamAttempt, loadExamPaper, loadExamPapers, saveExamResponses, submitExamAttempt } from '../api/learnerApi'
import { mobileApiClient } from '../api/mobileApi'
import { Body, Card, Field, Heading, Meta, PrimaryButton, ScreenScroll, StatusText } from '../components/primitives'
import type { NativeAudioCaptureResult } from '../native/NativeAudioBridge'
import { useMobileSpeechRecognition } from '../speech/useMobileSpeechRecognition'

export function ExamsScreen() {
  const { start, state: speechState, stop } = useMobileSpeechRecognition('en')
  const [papers, setPapers] = useState<ExamPaperSummary[]>([])
  const [paper, setPaper] = useState<ExamPaperDetail | null>(null)
  const [attemptId, setAttemptId] = useState<number | null>(null)
  const [lastCapture, setLastCapture] = useState<NativeAudioCaptureResult | null>(null)
  const [responses, setResponses] = useState<Record<number, string>>({})
  const [result, setResult] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    loadExamPapers()
      .then(setPapers)
      .catch(err => setError(err instanceof Error ? err.message : '真题加载失败'))
      .finally(() => setLoading(false))
  }, [])

  async function openPaper(id: number) {
    setLoading(true)
    setError('')
    try {
      const nextPaper = await loadExamPaper(id)
      setPaper(nextPaper)
      const nextAttemptId = await createExamAttempt(id)
      setAttemptId(nextAttemptId)
      setResponses({})
      setResult('')
    } catch (err) {
      setError(err instanceof Error ? err.message : '试卷打开失败')
    } finally {
      setLoading(false)
    }
  }

  async function saveAndSubmit() {
    if (!attemptId) return
    const drafts = Object.entries(responses).map(([questionId, responseText]) => ({
      questionId: Number(questionId),
      responseText,
      selectedChoices: [],
    }))
    await saveExamResponses(attemptId, drafts)
    const payload = await submitExamAttempt(attemptId)
    setResult(JSON.stringify(payload).slice(0, 1000))
  }

  async function evaluateSpeaking(question: ExamQuestion) {
    const form = new FormData()
    form.append('promptText', stripHtml(question.promptHtml))
    form.append('durationSeconds', String(lastCapture?.durationSeconds ?? 0))
    if (lastCapture?.fileUri) {
      form.append('audio', {
        uri: lastCapture.fileUri,
        type: lastCapture.mimeType || 'audio/wav',
        name: lastCapture.name || 'speaking-response.wav',
      } as unknown as Blob)
    }
    try {
      const payload = await mobileApiClient.json('/api/ai/speaking/evaluate', { method: 'POST', body: form })
      setResult(JSON.stringify(payload).slice(0, 1000))
    } catch (err) {
      setResult(err instanceof Error ? err.message : '口语评分暂时不可用')
    }
  }

  async function toggleSpeakingRecording(question: ExamQuestion) {
    if (speechState.status === 'recording') {
      const capture = await stop()
      setLastCapture(capture)
      if (speechState.finalText || speechState.partialText) {
        setResponses(prev => ({
          ...prev,
          [question.id]: speechState.finalText || speechState.partialText,
        }))
      }
      return
    }
    setLastCapture(null)
    await start()
  }

  const questions = paper?.sections.flatMap(section => section.questions) ?? []

  return (
    <ScreenScroll hideHeader title="真题" subtitle="试卷列表、答题、保存、提交；口语题支持录音与评分服务反馈。">
      <StatusText error={error} loading={loading} />
      {paper ? (
        <>
          <Card>
            <Heading>{paper.title}</Heading>
            <Meta>{paper.collectionTitle} · {paper.examKind}</Meta>
            <PrimaryButton label="返回试卷列表" tone="neutral" onPress={() => setPaper(null)} />
          </Card>
          {questions.map(question => (
            <Card key={question.id}>
              <Heading>题目 {question.questionNumber ?? question.id}</Heading>
              <Body>{stripHtml(question.promptHtml)}</Body>
              {question.choices.map(choice => (
                <PrimaryButton
                  key={choice.key}
                  label={`${choice.key}. ${stripHtml(choice.contentHtml)}`}
                  tone={responses[question.id] === choice.key ? 'primary' : 'neutral'}
                  onPress={() => setResponses(prev => ({ ...prev, [question.id]: choice.key }))}
                />
              ))}
              {!question.choices.length ? (
                <Field
                  value={responses[question.id] ?? ''}
                  onChangeText={value => setResponses(prev => ({ ...prev, [question.id]: value }))}
                  placeholder="输入答案"
                  multiline
                />
              ) : null}
              {question.questionType === 'speaking_prompt' ? (
                <>
                  <PrimaryButton
                    label={speechState.status === 'recording' ? '停止录音' : '录音'}
                    onPress={() => void toggleSpeakingRecording(question).catch(err => setError(err.message))}
                  />
                  <PrimaryButton label="请求 AI 评分" onPress={() => void evaluateSpeaking(question)} />
                  {speechState.error ? <Meta>{speechState.error}</Meta> : null}
                  {lastCapture?.fileUri ? <Meta>录音已保存，时长 {lastCapture.durationSeconds ?? 0}s</Meta> : null}
                  {speechState.partialText || speechState.finalText ? (
                    <Meta>{speechState.finalText || speechState.partialText}</Meta>
                  ) : null}
                </>
              ) : null}
            </Card>
          ))}
          <Card>
            <PrimaryButton label="保存并提交" onPress={() => void saveAndSubmit().catch(err => setError(err.message))} />
            {result ? <Meta>{result}</Meta> : null}
          </Card>
        </>
      ) : (
        papers.map(item => (
          <Card key={item.id}>
            <Heading>{item.title}</Heading>
            <Meta>{item.collectionTitle} · {item.examKind}</Meta>
            <PrimaryButton label="打开试卷" onPress={() => void openPaper(item.id)} />
          </Card>
        ))
      )}
      {!loading && !papers.length ? <Text>暂无真题。</Text> : null}
    </ScreenScroll>
  )
}
