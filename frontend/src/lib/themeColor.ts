export const THEME_COLOR_OPTIONS = [
  { value: 'red', label: '红色', description: '红色标签' },
  { value: 'orange', label: '橘色', description: 'Logo 橘色' },
  { value: 'yellow', label: '黄色', description: '黄色标签' },
  { value: 'green', label: '绿色', description: '浅绿色' },
  { value: 'blue', label: '蓝色', description: '蓝色标签' },
  { value: 'purple', label: '紫色', description: '紫色标签' },
  { value: 'gray', label: '灰色', description: '灰色标签' },
] as const

export type ThemeColor = typeof THEME_COLOR_OPTIONS[number]['value']

const VALID_THEME_COLORS = new Set<string>(THEME_COLOR_OPTIONS.map(option => option.value))

export function normalizeThemeColor(value: unknown): ThemeColor {
  return typeof value === 'string' && VALID_THEME_COLORS.has(value)
    ? (value as ThemeColor)
    : 'orange'
}

export function applyThemeColor(value: unknown): ThemeColor {
  const themeColor = normalizeThemeColor(value)
  if (typeof document !== 'undefined') {
    document.documentElement.setAttribute('data-accent-color', themeColor)
  }
  return themeColor
}
