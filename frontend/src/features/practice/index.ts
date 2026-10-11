// practice feature public surface.
//
// The practice feature is intentionally wide (15+ root files plus the audio/
// and gameMode/ subdirs). Cross-feature code should import the stable
// public surface below; private helpers (storage/ page presentation/ etc.)
// stay reachable through their deep paths until a clear reuse demand
// appears.

export * from './practiceOptions'
export * from './quickMemorySession'
export * from './wordPlayback'
export * from './errorReviewSession'
export * from './learnerProfile'
export * from './listeningInflections'
export * from './practiceGlobalShortcutEvents'
export * from './practiceSessionHelpers'
export * from './types'

// Confusable match domain (data + match logic only; storage/ presentation
// stay private deep-imported by the page composable).
export * from './confusableMatch'
export * from './confusableCustomGroups'

// Game mode (single-file subdir).
export * from './gameMode/gameData'
