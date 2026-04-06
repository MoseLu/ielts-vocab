import { useLayoutEffect, type RefObject } from 'react'

export function useBalancedStatsLayout({
  layoutRef,
  leftRef,
  topRef,
  bottomRef,
  deps,
}: {
  layoutRef: RefObject<HTMLDivElement>
  leftRef: RefObject<HTMLDivElement>
  topRef: RefObject<HTMLDivElement>
  bottomRef: RefObject<HTMLDivElement>
  deps: unknown[]
}) {
  useLayoutEffect(() => {
    const layoutEl = layoutRef.current
    const leftEl = leftRef.current
    const topEl = topRef.current
    const bottomEl = bottomRef.current
    if (!layoutEl || !leftEl || !topEl || !bottomEl) return

    const media = window.matchMedia('(min-width: 901px)')
    const gapPx = 10

    const syncBottomHeight = () => {
      if (!media.matches) {
        layoutEl.classList.remove('stats-main-layout--balanced')
        bottomEl.style.removeProperty('--stats-right-bottom-height')
        return
      }

      const leftHeight = Math.round(leftEl.getBoundingClientRect().height)
      const topHeight = Math.round(topEl.getBoundingClientRect().height)
      const availableHeight = Math.max(leftHeight - topHeight - gapPx, 320)

      layoutEl.classList.add('stats-main-layout--balanced')
      bottomEl.style.setProperty('--stats-right-bottom-height', `${availableHeight}px`)
    }

    syncBottomHeight()

    const resizeObserver = new ResizeObserver(syncBottomHeight)
    resizeObserver.observe(leftEl)
    resizeObserver.observe(topEl)

    media.addEventListener('change', syncBottomHeight)
    window.addEventListener('resize', syncBottomHeight)

    return () => {
      resizeObserver.disconnect()
      media.removeEventListener('change', syncBottomHeight)
      window.removeEventListener('resize', syncBottomHeight)
    }
  }, deps)
}
