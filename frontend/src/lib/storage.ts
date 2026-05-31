// LocalStorage helpers with JSON parsing and caller-provided fallbacks.
export function getStorageItem<T>(key: string, defaultValue: T): T {
  try {
    const item = localStorage.getItem(key)
    return item ? JSON.parse(item) : defaultValue
  } catch {
    return defaultValue
  }
}

export function setStorageItem<T>(key: string, value: T): void {
  localStorage.setItem(key, JSON.stringify(value))
}

export function trySetStorageItem(key: string, value: string): boolean {
  try {
    localStorage.setItem(key, value)
    return true
  } catch {
    return false
  }
}

export function setStorageJsonSafely<T>(key: string, value: T): boolean {
  try {
    return trySetStorageItem(key, JSON.stringify(value))
  } catch {
    return false
  }
}

export function removeStorageItem(key: string): void {
  localStorage.removeItem(key)
}
