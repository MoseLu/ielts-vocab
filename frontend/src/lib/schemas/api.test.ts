import { describe, expect, it } from 'vitest'

import { GameCampaignStateSchema } from './api'

describe('GameCampaignStateSchema', () => {
  it('accepts listening confusable entries with nullable group_key values', () => {
    const payload = {
      scope: { bookId: null, chapterId: null, day: null },
      campaign: {
        title: 'language',
        scopeLabel: '整本词书战役',
        totalWords: 3375,
        passedWords: 0,
        totalSegments: 675,
        clearedSegments: 0,
        currentSegment: 1,
      },
      segment: {
        index: 1,
        title: '第 1 试炼段',
        clearedWords: 0,
        totalWords: 5,
        bossStatus: 'locked',
        rewardStatus: 'locked',
      },
      currentNode: {
        nodeType: 'word',
        nodeKey: 'word:language',
        segmentIndex: 0,
        title: 'language',
        subtitle: '语言',
        status: 'pending',
        dimension: 'meaning',
        promptText: null,
        targetWords: ['language'],
        failedDimensions: ['meaning'],
        bossFailures: 0,
        rewardFailures: 0,
        lastEncounterType: null,
        word: {
          word: 'language',
          phonetic: '/ˈlæŋɡwɪdʒ/',
          pos: 'n.',
          definition: '语言',
          chapter_id: null,
          chapter_title: null,
          overall_status: 'new',
          current_round: 0,
          pending_dimensions: ['meaning'],
          listening_confusables: [
            {
              word: 'landscape',
              phonetic: '/ˈlændskeɪp/',
              pos: 'n.',
              definition: '景色',
              group_key: null,
            },
          ],
          examples: [{ en: 'Learning a new language takes time.', zh: '学习一门新语言需要时间。' }],
          dimension_states: {
            recognition: { status: 'passed', pass_streak: 4, attempt_count: 4, history_wrong: 0 },
            meaning: { status: 'not_started', pass_streak: 0, attempt_count: 0, history_wrong: 0 },
            listening: { status: 'not_started', pass_streak: 0, attempt_count: 0, history_wrong: 0 },
            speaking: { status: 'not_started', pass_streak: 0, attempt_count: 0, history_wrong: 0 },
            dictation: { status: 'not_started', pass_streak: 0, attempt_count: 0, history_wrong: 0 },
          },
          image: {
            status: 'queued',
            senseKey: 'language-n-sense',
            url: null,
            alt: 'language 词义配图',
            styleVersion: 'sense-scene-v2',
            model: 'wanx-v1',
            generatedAt: null,
          },
        },
      },
      nodeType: 'word',
      speakingBoss: null,
      speakingReward: null,
      recoveryPanel: {
        queue: [],
        bossQueue: [],
        recentMisses: [],
        resumeNode: null,
      },
    }

    const parsed = GameCampaignStateSchema.safeParse(payload)

    expect(parsed.success).toBe(true)
    expect(parsed.data?.hud).toEqual({
      playerLevel: 1,
      levelProgressPercent: 0,
      unreadMessages: 0,
    })
  })
})
