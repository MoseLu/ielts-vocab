import assert from 'node:assert/strict'
import { existsSync } from 'node:fs'
import { describe, it } from 'node:test'
import {
  stickerCatalog,
  stickerDefaults,
  stickerKeys,
  type StickerSlot,
} from '../src/components/stickers/catalog'
import {
  loginAgreementStickerSlots,
  practiceCompleteStickerSlots,
  practiceEntryStickerSlots,
  practiceSheetStickerSlots,
  studyRoomFeedbackStickerSlots,
  studyRoomStickerSlots,
} from '../src/components/stickers/presets'

const presetSlots: StickerSlot[] = [
  ...loginAgreementStickerSlots,
  ...practiceCompleteStickerSlots,
  ...practiceEntryStickerSlots,
  ...practiceSheetStickerSlots,
  ...studyRoomFeedbackStickerSlots,
  ...studyRoomStickerSlots,
]

const requiredTutorStickerKeys = [
  'catTutorIdle',
  'catTutorReading',
  'catTutorListening',
  'catTutorSpeaking',
  'catTutorWorried',
  'catTutorCelebrate',
  'catAgreement',
  'catCompanion',
  'vocabCardStack',
  'ieltsPaper',
  'headset',
  'recordingMic',
  'wrongWordSticky',
  'reviewClock',
  'aiLetter',
  'treasureChest',
  'studyWindow',
  'deskMat',
  'scrollNote',
  'leafSprig',
  'flowerSmall',
  'citrusCorner',
  'tapePin',
] as const

describe('mobile sticker catalog', () => {
  it('keeps catalog keys unique and backed by png assets', () => {
    assert.equal(new Set(stickerKeys).size, stickerKeys.length)

    for (const key of stickerKeys) {
      const meta = stickerCatalog[key]
      assert.match(meta.fileName, /^[a-z0-9-]+\.png$/)
      assert.ok(meta.width > 0)
      assert.ok(meta.height > 0)

      const assetPath = decodeURIComponent(new URL(`../src/assets/stickers/${meta.fileName}`, import.meta.url).pathname)
      assert.equal(existsSync(assetPath), true, `${meta.fileName} should exist`)
    }
  })

  it('references only known stickers from scene presets', () => {
    for (const slot of presetSlots) {
      assert.ok(stickerCatalog[slot.key], `${slot.key} should exist in catalog`)
      assert.ok(slot.width > 0)
      assert.ok(slot.height > 0)
    }
  })

  it('includes the IELTS tutor sticker library v1', () => {
    for (const key of requiredTutorStickerKeys) {
      assert.ok(stickerCatalog[key], `${key} should exist in catalog`)
    }
  })

  it('treats stickers as decorative by default', () => {
    assert.equal(stickerDefaults.decorative, true)
  })
})
