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
  | 'practiceModeDictation'
  | 'practiceModeFollow'
  | 'practiceModeListening'
  | 'practiceModeMeaning'
  | 'practiceModeQuickMemory'
  | 'practiceModeRadio'
  | 'practiceModeSmart'
  | 'practiceModeTest'
  | 'recordingMic'
  | 'reviewClock'
  | 'scrollNote'
  | 'studyWindow'
  | 'studyBadgePractice'
  | 'studyBadgeTodo'
  | 'studyBadgeWrong'
  | 'studyDecorBanner'
  | 'studyDecorMascot'
  | 'studyHeroBoard'
  | 'studyLoungeRoom'
  | 'tapePin'
  | 'treasureBox'
  | 'treasureChest'
  | 'uiCardFrameLarge'
  | 'uiCardFrameSmall'
  | 'uiSectionTitlePlaque'
  | 'uiScreenPaperBg'
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
  role: 'background' | 'character' | 'empty' | 'object' | 'plant'
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
  practiceModeDictation: { fileName: 'practice-mode-dictation.png', height: 360, role: 'object', width: 360 },
  practiceModeFollow: { fileName: 'practice-mode-follow.png', height: 360, role: 'object', width: 360 },
  practiceModeListening: { fileName: 'practice-mode-listening.png', height: 360, role: 'object', width: 360 },
  practiceModeMeaning: { fileName: 'practice-mode-meaning.png', height: 360, role: 'object', width: 360 },
  practiceModeQuickMemory: { fileName: 'practice-mode-quickmemory.png', height: 360, role: 'object', width: 360 },
  practiceModeRadio: { fileName: 'practice-mode-radio.png', height: 360, role: 'object', width: 360 },
  practiceModeSmart: { fileName: 'practice-mode-smart.png', height: 360, role: 'object', width: 360 },
  practiceModeTest: { fileName: 'practice-mode-test.png', height: 360, role: 'object', width: 360 },
  recordingMic: { fileName: 'recording-mic.png', height: 360, role: 'object', width: 360 },
  reviewClock: { fileName: 'review-clock.png', height: 300, role: 'object', width: 300 },
  scrollNote: { fileName: 'scroll-note.png', height: 240, role: 'object', width: 300 },
  studyWindow: { fileName: 'study-window.png', height: 360, role: 'object', width: 360 },
  studyBadgePractice: { fileName: 'study-badge-practice.png', height: 675, role: 'object', width: 612 },
  studyBadgeTodo: { fileName: 'study-badge-todo.png', height: 989, role: 'object', width: 865 },
  studyBadgeWrong: { fileName: 'study-badge-wrong.png', height: 997, role: 'object', width: 815 },
  studyDecorBanner: { fileName: 'study-decor-banner.png', height: 819, role: 'object', width: 467 },
  studyDecorMascot: { fileName: 'study-decor-mascot.png', height: 225, role: 'character', width: 228 },
  studyHeroBoard: { fileName: 'study-hero-board.png', height: 1114, role: 'object', width: 1391 },
  studyLoungeRoom: { fileName: 'study-lounge-room.png', height: 1024, role: 'object', width: 1536 },
  tapePin: { fileName: 'tape-pin.png', height: 360, role: 'object', width: 360 },
  treasureBox: { fileName: 'treasure-box.png', height: 300, role: 'object', width: 300 },
  treasureChest: { fileName: 'treasure-chest.png', height: 360, role: 'object', width: 360 },
  uiCardFrameLarge: { fileName: 'ui-card-frame-large.png', height: 1920, role: 'object', width: 1080 },
  uiCardFrameSmall: { fileName: 'ui-card-frame-small.png', height: 284, role: 'object', width: 900 },
  uiSectionTitlePlaque: { fileName: 'ui-section-title-plaque.png', height: 284, role: 'object', width: 900 },
  uiScreenPaperBg: { fileName: 'ui-screen-paper-bg.png', height: 2732, role: 'background', width: 1536 },
  vocabCardStack: { fileName: 'vocab-card-stack.png', height: 360, role: 'object', width: 360 },
  wrongWordSticky: { fileName: 'wrong-word-sticky.png', height: 360, role: 'object', width: 360 },
  wrongWordKit: { fileName: 'wrong-word-kit.png', height: 300, role: 'object', width: 300 },
}

export const stickerKeys = Object.keys(stickerCatalog) as StickerKey[]
