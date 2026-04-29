export function staticAssetUrl(path: string): string {
  const base = import.meta.env.BASE_URL || '/'
  const normalizedBase = base.endsWith('/') ? base : `${base}/`
  const cleanPath = path.replace(/^\/+/, '')
  return `${normalizedBase}${cleanPath}`
}
