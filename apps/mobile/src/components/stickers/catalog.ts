export type StickerKey =
  | 'aiLetter'
  | 'bookStack'
  | 'catAgreement'
  | 'catCompanion'
  | 'catTutorCelebrate'
  | 'catTutorIdle'
  | 'catTutorListening'
  | 'catTutorReading'
  | 'catTutorSpeaking'
  | 'catTutorWorried'
  | 'citrusCorner'
  | 'deskMat'
  | 'emptyAi'
  | 'emptyFeedback'
  | 'emptySearch'
  | 'emptyWrongWords'
  | 'flowerSmall'
  | 'headset'
  | 'ieltsPaper'
  | 'leafSprig'
  | 'lemonCorner'
  | 'micBubble'
  | 'recordingMic'
  | 'reviewClock'
  | 'scrollNote'
  | 'studyWindow'
  | 'tapePin'
  | 'treasureBox'
  | 'treasureChest'
  | 'vocabCardStack'
  | 'wrongWordSticky'
  | 'wrongWordKit'

export type StickerOffset = number | `${number}%`

export type StickerSlot = {
  bottom?: StickerOffset
  height: number
  key: StickerKey
  left?: StickerOffset
  opacity?: number
  right?: StickerOffset
  rotateDeg?: number
  top?: StickerOffset
  width: number
  zIndex?: number
}

export type StickerMeta = {
  fileName: string
  height: number
  role: 'character' | 'empty' | 'object' | 'plant'
  width: number
}

export const stickerDefaults = {
  decorative: true,
} as const

export const stickerCatalog: Record<StickerKey, StickerMeta> = {
  aiLetter: { fileName: 'ai-letter.png', height: 300, role: 'object', width: 300 },
  bookStack: { fileName: 'book-stack.png', height: 300, role: 'object', width: 300 },
  catAgreement: { fileName: 'cat-agreement.png', height: 360, role: 'character', width: 360 },
  catCompanion: { fileName: 'cat-companion.png', height: 360, role: 'character', width: 360 },
  catTutorCelebrate: { fileName: 'cat-tutor-celebrate.png', height: 360, role: 'character', width: 360 },
  catTutorIdle: { fileName: 'cat-tutor-idle.png', height: 360, role: 'character', width: 360 },
  catTutorListening: { fileName: 'cat-tutor-listening.png', height: 360, role: 'character', width: 360 },
  catTutorReading: { fileName: 'cat-tutor-reading.png', height: 360, role: 'character', width: 360 },
  catTutorSpeaking: { fileName: 'cat-tutor-speaking.png', height: 360, role: 'character', width: 360 },
  catTutorWorried: { fileName: 'cat-tutor-worried.png', height: 360, role: 'character', width: 360 },
  citrusCorner: { fileName: 'citrus-corner.png', height: 360, role: 'object', width: 360 },
  deskMat: { fileName: 'desk-mat.png', height: 540, role: 'object', width: 960 },
  emptyAi: { fileName: 'empty-ai.png', height: 300, role: 'empty', width: 360 },
  emptyFeedback: { fileName: 'empty-feedback.png', height: 300, role: 'empty', width: 360 },
  emptySearch: { fileName: 'empty-search.png', height: 300, role: 'empty', width: 360 },
  emptyWrongWords: { fileName: 'empty-wrong-words.png', height: 300, role: 'empty', width: 360 },
  flowerSmall: { fileName: 'flower-small.png', height: 180, role: 'plant', width: 180 },
  headset: { fileName: 'headset.png', height: 360, role: 'object', width: 360 },
  ieltsPaper: { fileName: 'ielts-paper.png', height: 360, role: 'object', width: 360 },
  leafSprig: { fileName: 'leaf-sprig.png', height: 210, role: 'plant', width: 240 },
  lemonCorner: { fileName: 'lemon-corner.png', height: 210, role: 'object', width: 240 },
  micBubble: { fileName: 'mic-bubble.png', height: 300, role: 'object', width: 300 },
  recordingMic: { fileName: 'recording-mic.png', height: 360, role: 'object', width: 360 },
  reviewClock: { fileName: 'review-clock.png', height: 300, role: 'object', width: 300 },
  scrollNote: { fileName: 'scroll-note.png', height: 240, role: 'object', width: 300 },
  studyWindow: { fileName: 'study-window.png', height: 360, role: 'object', width: 360 },
  tapePin: { fileName: 'tape-pin.png', height: 360, role: 'object', width: 360 },
  treasureBox: { fileName: 'treasure-box.png', height: 300, role: 'object', width: 300 },
  treasureChest: { fileName: 'treasure-chest.png', height: 360, role: 'object', width: 360 },
  vocabCardStack: { fileName: 'vocab-card-stack.png', height: 360, role: 'object', width: 360 },
  wrongWordSticky: { fileName: 'wrong-word-sticky.png', height: 360, role: 'object', width: 360 },
  wrongWordKit: { fileName: 'wrong-word-kit.png', height: 300, role: 'object', width: 300 },
}

export const stickerKeys = Object.keys(stickerCatalog) as StickerKey[]
