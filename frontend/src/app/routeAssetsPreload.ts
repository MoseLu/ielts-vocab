import { prdUiAsset } from '../components/practice/page/game-mode/prdUiAssets'
import { GAME_THEME_SELECT_CARD_URLS } from '../lib/gameThemeCardAssets'

function preloadImage(href: string, type?: string) {
  if (typeof document === 'undefined' || !href) return
  const existing = Array.from(
    document.head.querySelectorAll<HTMLLinkElement>('link[rel="preload"][as="image"]'),
  ).some(link => link.href === new URL(href, window.location.href).href)
  if (existing) return
  const link = document.createElement('link')
  link.rel = 'preload'
  link.as = 'image'
  link.href = href
  if (type) link.type = type
  document.head.appendChild(link)
}

export function preloadGameRouteAssets(pathname: string) {
  if (pathname === '/game/themes') {
    GAME_THEME_SELECT_CARD_URLS.forEach(url => preloadImage(url, 'image/webp'))
  }
  if (pathname.includes('/mission')) {
    preloadImage(prdUiAsset.templates.wordMission, 'image/avif')
  }
  if (pathname === '/game' || /^\/game\/themes\/[^/]+$/.test(pathname)) {
    preloadImage(prdUiAsset.templates.wordChainMap, 'image/avif')
  }
}
