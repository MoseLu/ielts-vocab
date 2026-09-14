import type { StickerSlot } from './catalog'

export const loginAgreementStickerSlots: StickerSlot[] = [
  { height: 84, key: 'leafSprig', left: 36, top: -44, width: 96, zIndex: 2 },
  { height: 128, key: 'catAgreement', right: 66, top: -116, width: 128, zIndex: 2 },
]

export const studyRoomStickerSlots: StickerSlot[] = [
  { bottom: -18, height: 226, key: 'deskMat', left: -58, opacity: 0.34, width: 404 },
  { height: 168, key: 'studyWindow', left: '34%', opacity: 0.34, top: 150, width: 168 },
  { height: 58, key: 'leafSprig', left: 72, opacity: 0.58, rotateDeg: -12, top: 72, width: 66 },
  { height: 42, key: 'flowerSmall', opacity: 0.56, right: 6, rotateDeg: 12, top: 384, width: 42 },
  { height: 54, key: 'ieltsPaper', right: 100, rotateDeg: -10, top: 292, width: 54 },
]

export const studyRoomFeedbackStickerSlots: StickerSlot[] = [
  { height: 72, key: 'catTutorCelebrate', left: 26, top: -40, width: 72, zIndex: 2 },
  { height: 44, key: 'citrusCorner', right: 26, rotateDeg: 8, top: 18, width: 44, zIndex: 2 },
]

export const practiceEntryStickerSlots: StickerSlot[] = [
  { height: 58, key: 'vocabCardStack', right: 16, rotateDeg: 6, top: 12, width: 58 },
]

export const practiceSheetStickerSlots: StickerSlot[] = [
  { height: 44, key: 'scrollNote', left: 64, rotateDeg: -6, top: -30, width: 56 },
  { height: 38, key: 'flowerSmall', opacity: 0.82, right: 22, rotateDeg: 12, top: 22, width: 38 },
]

export const practiceCompleteStickerSlots: StickerSlot[] = [
  { height: 84, key: 'catTutorCelebrate', right: 20, top: 12, width: 84 },
  { bottom: 18, height: 52, key: 'reviewClock', left: 18, rotateDeg: -8, width: 52 },
]

export const modeStickerKeys = {
  ebbinghaus: 'reviewClock',
  errors: 'wrongWordSticky',
  follow: 'recordingMic',
  regular: 'vocabCardStack',
  speaking: 'aiLetter',
} as const
