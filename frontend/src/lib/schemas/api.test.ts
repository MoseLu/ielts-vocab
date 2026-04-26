import { describe, expect, it } from 'vitest'

import { GameCampaignStateSchema, GameThemeCatalogSchema } from './api'

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
        title: '第 1 词链',
        clearedWords: 0,
        totalWords: 5,
        bossStatus: 'locked',
        rewardStatus: 'locked',
      },
      taskFocus: {
        task: 'error-review',
        dimension: 'meaning',
        book: 'ielts_reading_premium',
        chapter: '1',
      },
      mapPath: {
        currentNodeKey: 'word:language',
        totalNodes: 2,
        nodes: [
          {
            nodeType: 'word',
            nodeKey: 'word:language',
            index: 1,
            title: 'language',
            subtitle: '语言',
            status: 'current',
            dimension: 'meaning',
            failedDimensions: ['meaning'],
          },
          {
            nodeType: 'word',
            nodeKey: 'word:landscape',
            index: 2,
            title: 'landscape',
            subtitle: '景色',
            status: 'locked',
            dimension: null,
            failedDimensions: [],
          },
        ],
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
    expect(parsed.data?.taskFocus?.task).toBe('error-review')
    expect(parsed.data?.mapPath?.nodes[0]?.status).toBe('current')
    expect(parsed.data?.hud).toEqual({
      playerLevel: 1,
      levelProgressPercent: 0,
      unreadMessages: 0,
    })
  })

  it('accepts optional theme state fields while preserving legacy defaults', () => {
    const payload = {
      scope: {
        bookId: null,
        chapterId: null,
        day: null,
        themeId: 'science-tech',
        themeChapterId: 'science-tech-1',
      },
      campaign: {
        title: 'technology',
        scopeLabel: '科技科学 · 第 1 页',
        totalWords: 64,
        passedWords: 8,
        totalSegments: 13,
        clearedSegments: 1,
        currentSegment: 2,
      },
      segment: {
        index: 2,
        title: '科技科学 02',
        clearedWords: 3,
        totalWords: 5,
        bossStatus: 'locked',
        rewardStatus: 'locked',
      },
      currentNode: null,
      nodeType: null,
      speakingBoss: null,
      speakingReward: null,
      theme: {
        id: 'science-tech',
        title: '科技科学',
        subtitle: 'Technology and science vocabulary',
        wordCount: 930,
        totalChapters: 8,
        assets: {
          desktopMap: '/game/campaign-v2/themes/science-tech/desktop/map.png',
          mobileMap: '/game/campaign-v2/themes/science-tech/mobile/map.png',
          selectCard: '/game/campaign-v2/themes/science-tech/desktop/select-card.png',
          emptyState: '/game/campaign-v2/themes/science-tech/desktop/empty-state.png',
        },
      },
      themeChapter: {
        id: 'science-tech-1',
        title: '科技科学 01',
        wordCount: 64,
        page: 1,
        bookIds: ['ielts_reading_premium', 'ielts_listening_premium'],
      },
      themeProgress: {
        currentPage: 1,
        pageSize: 8,
        totalPages: 1,
        chapterOffset: 0,
      },
      recoveryPanel: {
        queue: [],
        bossQueue: [],
        recentMisses: [],
        resumeNode: null,
      },
    }

    const parsed = GameCampaignStateSchema.safeParse(payload)

    expect(parsed.success).toBe(true)
    expect(parsed.data?.scope.themeId).toBe('science-tech')
    expect(parsed.data?.theme?.assets.desktopMap).toContain('/campaign-v2/')
    expect(parsed.data?.themeProgress?.pageSize).toBe(8)
  })
})

describe('GameThemeCatalogSchema', () => {
  it('accepts the static IELTS theme catalog contract', () => {
    const parsed = GameThemeCatalogSchema.safeParse({
      sourceBooks: ['ielts_reading_premium', 'ielts_listening_premium'],
      totalWords: 7269,
      pageSize: 8,
      themes: [
        {
          id: 'study-campus',
          title: '教育校园',
          subtitle: 'Education, campus, training and academic life',
          description: 'IELTS 学习、校园、培训与学术生活词汇。',
          wordCount: 900,
          totalChapters: 8,
          chapters: [
            {
              id: 'study-campus-1',
              title: '教育校园 01',
              wordCount: 72,
              page: 1,
              bookIds: ['ielts_reading_premium'],
            },
          ],
          assets: {
            desktopMap: '/game/campaign-v2/themes/study-campus/desktop/map.png',
            mobileMap: '/game/campaign-v2/themes/study-campus/mobile/map.png',
            selectCard: '/game/campaign-v2/themes/study-campus/desktop/select-card.png',
            emptyState: '/game/campaign-v2/themes/study-campus/desktop/empty-state.png',
          },
        },
      ],
    })

    expect(parsed.success).toBe(true)
    expect(parsed.data?.themes[0]?.chapters[0]?.page).toBe(1)
  })
})
