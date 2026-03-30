import { useEffect, useRef, useState } from 'react'
import {
  calculateChapterModalSkeletonCount,
  calculatePageSkeletonCount,
  estimateChapterModalBodyHeight,
} from '../lib/responsiveSkeleton'

interface ResponsivePageSkeletonOptions {
  minColumnWidth: number
  gap?: number
}

interface ResponsiveChapterSkeletonOptions {
  rowMinHeight?: number
  gap?: number
  maxRows?: number
}

function readElementWidth(element: HTMLElement | null): number {
  if (!element) return 0
  return Math.round(element.clientWidth || element.getBoundingClientRect().width || 0)
}

function readElementHeight(element: HTMLElement | null): number {
  if (!element) return 0
  return Math.round(element.clientHeight || element.getBoundingClientRect().height || 0)
}

export function useResponsivePageSkeletonCount({
  minColumnWidth,
  gap = 10,
}: ResponsivePageSkeletonOptions) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const [count, setCount] = useState(() => {
    const viewportWidth = typeof window === 'undefined' ? 0 : window.innerWidth
    return calculatePageSkeletonCount({ viewportWidth, minColumnWidth, gap })
  })

  useEffect(() => {
    if (typeof window === 'undefined') return undefined

    const update = () => {
      setCount(
        calculatePageSkeletonCount({
          viewportWidth: window.innerWidth,
          minColumnWidth,
          gap,
          containerWidth: readElementWidth(containerRef.current),
        }),
      )
    }

    update()

    const resizeObserver = typeof ResizeObserver === 'undefined'
      ? null
      : new ResizeObserver(update)

    if (containerRef.current && resizeObserver) {
      resizeObserver.observe(containerRef.current)
    }

    window.addEventListener('resize', update)

    return () => {
      resizeObserver?.disconnect()
      window.removeEventListener('resize', update)
    }
  }, [gap, minColumnWidth])

  return { containerRef, count }
}

export function useResponsiveChapterSkeletonCount({
  rowMinHeight = 156,
  gap = 10,
  maxRows = 3,
}: ResponsiveChapterSkeletonOptions = {}) {
  const bodyRef = useRef<HTMLDivElement | null>(null)
  const [count, setCount] = useState(() => {
    if (typeof window === 'undefined') return 6

    return calculateChapterModalSkeletonCount({
      viewportWidth: window.innerWidth,
      bodyHeight: estimateChapterModalBodyHeight(window.innerHeight),
      rowMinHeight,
      gap,
      maxRows,
    })
  })

  useEffect(() => {
    if (typeof window === 'undefined') return undefined

    const update = () => {
      const measuredHeight = readElementHeight(bodyRef.current)

      setCount(
        calculateChapterModalSkeletonCount({
          viewportWidth: window.innerWidth,
          bodyHeight: measuredHeight || estimateChapterModalBodyHeight(window.innerHeight),
          rowMinHeight,
          gap,
          maxRows,
        }),
      )
    }

    update()

    const resizeObserver = typeof ResizeObserver === 'undefined'
      ? null
      : new ResizeObserver(update)

    if (bodyRef.current && resizeObserver) {
      resizeObserver.observe(bodyRef.current)
    }

    window.addEventListener('resize', update)

    return () => {
      resizeObserver?.disconnect()
      window.removeEventListener('resize', update)
    }
  }, [gap, maxRows, rowMinHeight])

  return { bodyRef, count }
}
