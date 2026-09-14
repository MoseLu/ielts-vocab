import { STORAGE_KEYS } from '../constants'

export const APP_STORAGE_SCHEMA_VERSION = '2026-06-01-release-state-v1'
export const APP_STORAGE_SCHEMA_VERSION_KEY = 'ielts_vocab_app_storage_schema_version'

const SAFE_RELEASE_RESET_KEYS = [
  'study_plan',
  'selected_book',
  'selected_chapter',
  'chapter_start_index',
  'active_study_session_skip_recovery_until',
  STORAGE_KEYS.CURRENT_DAY,
  STORAGE_KEYS.CURRENT_MODE,
  STORAGE_KEYS.ACTIVE_STUDY_SESSION,
]

const SAFE_RELEASE_RESET_PREFIXES = [
  'local_storage_migration_v1_done:user:',
]

export function ensureAppStorageSchemaVersion() {
  try {
    if (localStorage.getItem(APP_STORAGE_SCHEMA_VERSION_KEY) === APP_STORAGE_SCHEMA_VERSION) {
      return
    }

    for (const key of SAFE_RELEASE_RESET_KEYS) {
      localStorage.removeItem(key)
    }

    for (let index = localStorage.length - 1; index >= 0; index -= 1) {
      const key = localStorage.key(index)
      if (!key) continue
      if (SAFE_RELEASE_RESET_PREFIXES.some(prefix => key.startsWith(prefix))) {
        localStorage.removeItem(key)
      }
    }

    localStorage.setItem(APP_STORAGE_SCHEMA_VERSION_KEY, APP_STORAGE_SCHEMA_VERSION)
  } catch {
    // localStorage can be blocked; startup should keep working without the reset gate.
  }
}
