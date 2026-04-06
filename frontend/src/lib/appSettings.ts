import { DEFAULT_SETTINGS, STORAGE_KEYS } from '../constants'
import type { AppSettings } from '../types'

const VALID_REVIEW_INTERVALS = new Set(['1', '3', '7'])
function asSettingsRecord(value: unknown): AppSettings {
  return typeof value === 'object' && value !== null
    ? (value as AppSettings)
    : {}
}

export function normalizeAppSettings(value: unknown): AppSettings {
  const candidate = asSettingsRecord(value)
  const normalized: AppSettings = {
    ...DEFAULT_SETTINGS,
    ...candidate,
  }

  const reviewInterval = String(candidate.reviewInterval ?? normalized.reviewInterval ?? DEFAULT_SETTINGS.reviewInterval)
  normalized.reviewInterval = VALID_REVIEW_INTERVALS.has(reviewInterval)
    ? reviewInterval
    : DEFAULT_SETTINGS.reviewInterval

  const rawReviewLimit = String(candidate.reviewLimit ?? normalized.reviewLimit ?? DEFAULT_SETTINGS.reviewLimit)
  const explicitReviewLimit = candidate.reviewLimitCustomized === true
  const parsedReviewLimit = parseInt(rawReviewLimit, 10)
  const validReviewLimit = rawReviewLimit === 'unlimited'
    ? 'unlimited'
    : Number.isFinite(parsedReviewLimit) && parsedReviewLimit > 0
      ? String(parsedReviewLimit)
      : DEFAULT_SETTINGS.reviewLimit

  normalized.reviewLimitCustomized = explicitReviewLimit
  normalized.reviewLimit = explicitReviewLimit
    ? validReviewLimit
    : DEFAULT_SETTINGS.reviewLimit

  return normalized
}

export function readAppSettingsFromStorage(): AppSettings {
  try {
    const saved = localStorage.getItem(STORAGE_KEYS.APP_SETTINGS)
    if (!saved) return normalizeAppSettings(DEFAULT_SETTINGS)
    const parsed = JSON.parse(saved)
    const normalized = normalizeAppSettings(parsed)
    if (JSON.stringify(normalized) !== JSON.stringify(parsed)) {
      localStorage.setItem(STORAGE_KEYS.APP_SETTINGS, JSON.stringify(normalized))
    }
    return normalized
  } catch {
    return normalizeAppSettings(DEFAULT_SETTINGS)
  }
}

export function writeAppSettingsToStorage(settings: AppSettings): AppSettings {
  const normalized = normalizeAppSettings(settings)
  localStorage.setItem(STORAGE_KEYS.APP_SETTINGS, JSON.stringify(normalized))
  return normalized
}
