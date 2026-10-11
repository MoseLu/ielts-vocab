import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import FollowReadScoreDetails from './FollowReadScoreDetails'

describe('FollowReadScoreDetails', () => {
  it('keeps the score lightweight and expands phoneme details on click', async () => {
    const user = userEvent.setup()
    render(
      <FollowReadScoreDetails
        label="通过"
        summary="发音整体清晰，继续保持。"
        result={{
          word: 'language',
          score: 86,
          band: 'pass',
          passed: true,
          transcript: 'language',
          feedback: {
            summary: '发音整体清晰，继续保持。',
            stress: '重音稳定。',
            vowel: '元音稳定。',
            consonant: '辅音稳定。',
            ending: '收音完整。',
            rhythm: '韵律仅供参考。',
          },
          weakSegments: [],
          segmentFeedback: [
            { text: 'lan', phonetic: 'læŋ', score: 90, status: 'good' },
          ],
          phonemeFeedback: [
            {
              expectedPhoneme: 'æ',
              score: 88,
              status: 'good',
              candidatePhonemes: [{ phoneme: 'e', confidence: 62 }],
            },
          ],
          dimensions: {
            phonemeAccuracy: 86,
            completeness: 92,
            fluency: 81,
            prosody: 75,
          },
        }}
      />,
    )

    expect(screen.getByText('86')).toBeInTheDocument()
    expect(screen.queryByText('/æ/')).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /点击查看逐音素详情/ }))

    expect(screen.getByText('/æ/')).toBeInTheDocument()
    expect(screen.getByText('音素准确度 86')).toBeInTheDocument()
    expect(screen.getByText('可能读成 /e/ 62')).toBeInTheDocument()
  })
})
