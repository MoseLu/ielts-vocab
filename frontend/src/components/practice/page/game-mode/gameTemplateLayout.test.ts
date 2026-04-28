import { describe, expect, it } from 'vitest'

import {
  GAME_TEMPLATE_LAYOUTS,
  assertTemplateSlots,
  findTemplateSlot,
  layoutSlotStyle,
  responsiveLayoutSlotStyle,
  validateGameTemplateLayouts,
} from './gameTemplateLayout'

describe('game template layout manifest', () => {
  it('defines slot contracts for every high-fidelity game template', () => {
    expect(Object.keys(GAME_TEMPLATE_LAYOUTS).sort()).toEqual([
      'learningCenter',
      'mobileWordChainMap',
      'mobileWordMission',
      'refillState',
      'stageSettlement',
      'wordChainMap',
      'wordMission',
    ])

    assertTemplateSlots('wordChainMap', [
      'map.title',
      'map.word.1',
      'map.word.5',
      'map.refill',
      'map.boss',
      'map.reward',
      'map.hud.energy',
      'map.hud.coins',
      'map.hud.diamonds',
      'map.side.word',
      'map.action',
      'map.bottom.word',
      'map.bottom.progress',
    ])
    assertTemplateSlots('mobileWordChainMap', [
      'map.title',
      'map.word.1',
      'map.word.5',
      'map.refill',
      'map.boss',
      'map.reward',
      'map.hud.energy',
      'map.hud.coins',
      'map.hud.diamonds',
      'map.side.word',
      'map.action',
      'map.bottom.word',
      'map.bottom.progress',
    ])
    assertTemplateSlots('wordMission', ['mission.hud', 'mission.objective', 'mission.answerPanel'])
    assertTemplateSlots('refillState', [
      'refill.hud',
      'refill.list',
      'refill.objective',
      'refill.answerPanel',
      'refill.action',
    ])
    assertTemplateSlots('stageSettlement', ['settlement.medal', 'settlement.copy', 'settlement.rewards', 'settlement.actions'])
    assertTemplateSlots('learningCenter', ['learningCenter.hero', 'learningCenter.todayPlan', 'learningCenter.actions'])
    assertTemplateSlots('mobileWordMission', ['mobileMission.hud', 'mobileMission.objective', 'mobileMission.answerPanel'])
  })

  it('converts source pixel slots into stable CSS percentages', () => {
    expect(layoutSlotStyle('wordChainMap', 'map.word.3')).toMatchObject({
      '--template-slot-left': '31.9042%',
      '--template-slot-top': '46.7742%',
      '--template-slot-width': '9.4578%',
      '--template-slot-height': '4.2339%',
    })
    expect(layoutSlotStyle('wordChainMap', 'map.word.3')).toMatchObject({
      '--template-slot-center-x': '36.6330%',
      '--template-slot-center-y': '48.8911%',
    })
  })

  it('throws a clear error when a required slot is missing', () => {
    expect(() => findTemplateSlot('wordChainMap', 'map.word.404')).toThrow(
      'Missing game template slot "map.word.404" in "wordChainMap"',
    )
  })

  it('carries mobile-specific slot variables when a mobile template replaces the desktop art', () => {
    expect(
      responsiveLayoutSlotStyle('wordMission', 'mission.answerPanel', 'mobileWordMission', 'mobileMission.answerPanel'),
    ).toMatchObject({
      '--template-slot-left': '4.0353%',
      '--template-mobile-slot-left': '6.7995%',
      '--template-mobile-slot-top': '68.3297%',
      '--template-mobile-slot-width': '86.2837%',
    })
  })

  it('keeps the mobile word-chain map on its own portrait coordinate system', () => {
    expect(GAME_TEMPLATE_LAYOUTS.mobileWordChainMap.naturalSize).toEqual({
      width: 853,
      height: 1844,
    })
    expect(layoutSlotStyle('mobileWordChainMap', 'map.word.3')).toMatchObject({
      '--template-slot-left': '33.9977%',
      '--template-slot-top': '41.7570%',
      '--template-slot-width': '25.7913%',
      '--template-slot-height': '2.9284%',
    })
  })

  it('validates assets, dimensions, required slots, and overlapping required slots', () => {
    expect(validateGameTemplateLayouts()).toEqual([])
  })
})
