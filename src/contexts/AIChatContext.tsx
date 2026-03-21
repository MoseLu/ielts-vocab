import React from 'react'
import type { LearningContext } from '../types'

// ── Global store for cross-module context logging ────────────────────────────────
// Any component can import this and call setGlobalLearningContext(ctx)
// The AIChatPanel will pick it up via its useAIChat hook and include it in requests.

let _currentContext: LearningContext = {}

export function setGlobalLearningContext(ctx: LearningContext) {
  _currentContext = { ..._currentContext, ...ctx }
}

export function clearGlobalLearningContext() {
  _currentContext = {}
}

export function getGlobalLearningContext(): LearningContext {
  return _currentContext
}
