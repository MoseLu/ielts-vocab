import { render, screen } from '@testing-library/react'

import type { GameCampaignState, GameLevelCard, GameMapPathNode } from '../../../../lib'
import { GameMapShell } from './GameMapShell'

function wordNode(index: number, title: string, status: GameMapPathNode['status']): GameMapPathNode {
  return {
    nodeType: 'word',
    nodeKey: `word:${title}`,
    index,
    title,
    subtitle: null,
    status,
    dimension: null,
    failedDimensions: status === 'refill' ? ['meaning'] : [],
  }
}

function buildState(nodes: GameMapPathNode[]): GameCampaignState {
  return {
    scope: { bookId: 'ielts_reading_premium', chapterId: '1', day: null },
    campaign: {
      title: '雅思阅读高频词汇',
      scopeLabel: '章节词关',
      totalWords: 64,
      passedWords: 0,
      totalSegments: 13,
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
      words: nodes.map(node => node.title),
    },
    taskFocus: {
      task: 'continue-book',
      dimension: null,
      book: 'ielts_reading_premium',
      chapter: '1',
    },
    mapPath: {
      currentNodeKey: nodes[0]?.nodeKey ?? null,
      totalNodes: nodes.length,
      nodes,
    },
    currentNode: {
      nodeType: 'word',
      nodeKey: nodes[0]?.nodeKey ?? 'word:language',
      segmentIndex: 0,
      title: nodes[0]?.title ?? 'language',
      subtitle: null,
      status: 'pending',
      dimension: null,
      levelKind: 'spelling',
      levelLabel: '拼写强化',
      promptText: null,
      targetWords: [nodes[0]?.title ?? 'language'],
      failedDimensions: [],
      bossFailures: 0,
      rewardFailures: 0,
      lastEncounterType: null,
      word: { word: nodes[0]?.title ?? 'language' },
    },
    rewards: {
      coins: 80,
      diamonds: 0,
      exp: 0,
      stars: 0,
      chest: 'normal',
      bestHits: 0,
    },
    session: {
      status: 'launcher',
      score: 0,
      hits: 0,
      bestHits: 0,
      hintsRemaining: 2,
      hintUsage: 0,
      energy: 5,
      energyMax: 5,
      nextEnergyAt: null,
      enabledBoosts: { spellingBoost: true, applicationBoost: true },
      resultOverlay: null,
      boostModule: null,
    },
    levelCards: [] as GameLevelCard[],
    boostModule: null,
  } as unknown as GameCampaignState
}

describe('GameMapShell', () => {
  it('lays out repeated refill word nodes without stacking them on one map coordinate', () => {
    const nodes = [
      wordNode(1, 'language', 'current'),
      wordNode(2, 'understanding', 'refill'),
      wordNode(3, 'without', 'refill'),
      wordNode(4, 'within', 'refill'),
      wordNode(5, 'required', 'refill'),
    ]

    render(
      <GameMapShell
        state={buildState(nodes)}
        levelCards={[]}
        isStarting={false}
        error={null}
        onStart={() => {}}
      />,
    )

    expect(screen.getByRole('region', { name: '五维词关地图' })).toBeInTheDocument()
    const slotIds = Array.from(document.querySelectorAll<HTMLElement>('.practice-game-map__segment-label'))
      .map(label => label.dataset.layoutSlot)

    expect(slotIds).toEqual([
      'map.word.1',
      'map.word.2',
      'map.word.3',
      'map.word.4',
      'map.word.5',
      'map.boss',
      'map.refill',
      'map.reward',
    ])
    expect(screen.getByText('without').closest('.practice-game-map__segment-label')).toHaveStyle({
      '--template-slot-left': '31.9042%',
      '--template-slot-top': '46.7742%',
    })
    expect(screen.getByText('understanding').closest('.practice-game-map__segment-label')).toHaveStyle({
      '--map-label-font-size': 'clamp(var(--size-6), 0.8vw, var(--size-10))',
    })
    expect(screen.getByLabelText('体力')).toHaveAttribute('data-layout-slot', 'map.hud.energy')
    expect(screen.getByLabelText('体力')).toHaveStyle({ '--template-mobile-slot-left': '55.6858%' })
    expect(screen.getByLabelText('金币')).toHaveAttribute('data-layout-slot', 'map.hud.coins')
    expect(screen.getByLabelText('金币')).toHaveStyle({ '--template-slot-left': '62.5473%' })
    expect(screen.getByLabelText('金币')).toHaveStyle({ '--template-mobile-slot-left': '11.7233%' })
    expect(screen.getByLabelText('钻石')).toHaveAttribute('data-layout-slot', 'map.hud.diamonds')
    expect(screen.getByLabelText('当前词')).toHaveAttribute('data-layout-slot', 'map.side.word')
    expect(screen.getByLabelText('底部当前词')).toHaveAttribute('data-layout-slot', 'map.bottom.word')
    expect(screen.getByLabelText('底部进度')).toHaveAttribute('data-layout-slot', 'map.bottom.progress')
    expect(screen.getByLabelText('底部进度')).toHaveStyle({ '--template-mobile-slot-top': '87.6356%' })
    expect(document.querySelector('source[media="(max-width: 640px)"]')).toHaveAttribute(
      'srcset',
      expect.stringContaining('/ui/templates/mobile-word-chain-map-text-safe.png'),
    )
    expect(document.querySelector('[data-layout-slot="map.boss"] strong')).toHaveTextContent('Boss')
    expect(document.querySelector('[data-layout-slot="map.refill"] strong')).toHaveTextContent('回流')
    expect(document.querySelector('[data-layout-slot="map.reward"] strong')).toHaveTextContent('宝箱')
    expect(screen.queryByLabelText('站内信')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '退出地图' })).not.toBeInTheDocument()
    expect(document.querySelector('[data-layout-slot="map.hud"]')).toBeNull()
    expect(document.querySelector('[data-layout-slot="map.hud.messages"]')).toBeNull()
    expect(document.querySelector('[data-layout-slot="map.exit"]')).toBeNull()
    expect(document.querySelector('[data-layout-slot="map.sidePanel"]')).toBeNull()
    expect(document.querySelector('[data-layout-slot="map.bottomStatus"]')).toBeNull()
    expect(document.querySelector('.practice-game-map__segment-label')?.closest('.practice-game-map__segment-node')).toBeNull()
  })

  it('keeps long live word labels inside their manifest slot with full text available', () => {
    const longWord = 'pneumonoultramicroscopicsilicovolcanoconiosis'
    const nodes = [
      wordNode(1, 'language', 'cleared'),
      wordNode(2, longWord, 'current'),
      wordNode(3, 'analysis', 'locked'),
    ]

    render(
      <GameMapShell
        state={buildState(nodes)}
        levelCards={[]}
        isStarting={false}
        error={null}
        onStart={() => {}}
      />,
    )

    const label = screen.getByText(longWord).closest('.practice-game-map__segment-label')

    expect(label).toHaveAttribute('data-layout-slot', 'map.word.2')
    expect(label).toHaveAttribute('title', longWord)
    expect(label).toHaveStyle({ '--map-label-scale': '0.68' })
    expect(label).toHaveStyle({
      '--map-label-font-size': 'clamp(var(--size-6), 0.55vw, var(--size-8))',
    })
    expect(label).toHaveStyle({
      '--template-slot-width': '9.8361%',
      '--template-slot-height': '4.2339%',
    })
  })

  it('labels the visible route as a five-word segment and keeps full-chain progress separate', () => {
    const nodes = [
      wordNode(1, 'language', 'current'),
      wordNode(2, 'understanding', 'locked'),
      wordNode(3, 'without', 'locked'),
      wordNode(4, 'within', 'locked'),
      wordNode(5, 'required', 'locked'),
    ]

    render(
      <GameMapShell
        state={buildState(nodes)}
        levelCards={[]}
        isStarting={false}
        error={null}
        onStart={() => {}}
      />,
    )

    expect(screen.getByLabelText('小段标题')).toBeInTheDocument()
    expect(screen.getByText('当前 5 词小段')).toBeInTheDocument()
    expect(screen.getByText('第 1 小段 / 共 13 段')).toBeInTheDocument()
    expect(screen.getByText('小段进度')).toBeInTheDocument()
    expect(screen.getByText('0 / 5 词')).toBeInTheDocument()
    expect(screen.getByText('全链词汇进度')).toBeInTheDocument()
    expect(screen.getByText('0 / 64')).toBeInTheDocument()
    expect(screen.getByText('主线新词 · 小段 1/13 · 全链 0/64')).toBeInTheDocument()
    expect(screen.getByText('主线新词 · 小段 1/13 · 全链 0/64')).toHaveAttribute('data-layout-slot', 'map.bottom.progress')
    expect(screen.queryByText('词链防线地图')).not.toBeInTheDocument()
    expect(screen.queryByText('当前词链 1 / 13')).not.toBeInTheDocument()
    expect(screen.queryByText('词链进度')).not.toBeInTheDocument()
  })

  it('shows the real word count when the current segment is shorter than five words', () => {
    const nodes = [
      wordNode(1, 'alpha', 'current'),
      wordNode(2, 'beta', 'locked'),
      wordNode(3, 'gamma', 'locked'),
    ]
    const state = buildState(nodes)
    state.campaign.totalWords = 63
    state.campaign.totalSegments = 13
    state.campaign.currentSegment = 13
    state.segment.index = 13
    state.segment.totalWords = 3
    state.segment.words = nodes.map(node => node.title)

    render(
      <GameMapShell
        state={state}
        levelCards={[]}
        isStarting={false}
        error={null}
        onStart={() => {}}
      />,
    )

    expect(screen.getByText('当前 3 词小段')).toBeInTheDocument()
    expect(screen.getByText('第 13 小段 / 共 13 段')).toBeInTheDocument()
  })
})
