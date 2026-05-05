import { beforeEach, describe, expect, it, vi } from 'vitest'
import { __setApiBaseOverrideForTests, setAuthAccessExpiry, setAuthSessionActive } from './index'
import { submitWordMasteryAttempt } from './gamePractice'

function gameAttemptResponse() {
  return {
    state: {
      nodeType: 'word',
      status: 'passed',
      failedDimensions: [],
    },
    game_state: {
      scope: {},
      campaign: {
        title: '五维词关',
        scopeLabel: 'Book 1',
        totalWords: 1,
        passedWords: 1,
        totalSegments: 1,
        clearedSegments: 1,
        currentSegment: 0,
      },
      segment: {
        index: 0,
        title: 'Segment 1',
        clearedWords: 1,
        totalWords: 1,
        bossStatus: 'locked',
        rewardStatus: 'locked',
      },
      currentNode: null,
      nodeType: null,
      speakingBoss: null,
      speakingReward: null,
      recoveryPanel: {
        queue: [],
        bossQueue: [],
        recentMisses: [],
        resumeNode: null,
      },
    },
  }
}

describe('game practice requests', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setAuthSessionActive(false)
    setAuthAccessExpiry(null)
    __setApiBaseOverrideForTests(null)
  })

  it('sends clientAttemptId as the idempotency header for mastery attempts', async () => {
    vi.mocked(global.fetch).mockResolvedValueOnce(
      new Response(JSON.stringify(gameAttemptResponse()), { status: 200 }),
    )

    await submitWordMasteryAttempt({
      word: 'abandon',
      dimension: 'meaning',
      passed: true,
      clientAttemptId: 'attempt-123',
    })

    const [, options] = vi.mocked(global.fetch).mock.calls[0] ?? []
    const headers = new Headers(options?.headers)
    const body = JSON.parse(String(options?.body))
    expect(headers.get('Idempotency-Key')).toBe('attempt-123')
    expect(headers.get('X-Trace-Id')).toBeNull()
    expect(body.clientAttemptId).toBe('attempt-123')
  })

  it('lets an explicit idempotency key override the legacy clientAttemptId', async () => {
    vi.mocked(global.fetch).mockResolvedValueOnce(
      new Response(JSON.stringify(gameAttemptResponse()), { status: 200 }),
    )

    await submitWordMasteryAttempt({
      word: 'abandon',
      dimension: 'meaning',
      passed: true,
      clientAttemptId: 'legacy-attempt',
      idempotencyKey: 'practice:session-1:game:theme-1:abandon:meaning:0',
      traceId: 'practice:trace-1',
    })

    const [, options] = vi.mocked(global.fetch).mock.calls[0] ?? []
    const headers = new Headers(options?.headers)
    const body = JSON.parse(String(options?.body))
    expect(headers.get('Idempotency-Key')).toBe('practice:session-1:game:theme-1:abandon:meaning:0')
    expect(headers.get('X-Trace-Id')).toBe('practice:trace-1')
    expect(body.clientAttemptId).toBe('practice:session-1:game:theme-1:abandon:meaning:0')
    expect(body.traceId).toBe('practice:trace-1')
  })
})
