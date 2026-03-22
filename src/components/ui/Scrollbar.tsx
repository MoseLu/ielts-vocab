// ── Scrollbar ────────────────────────────────────────────────────────────────
// Custom scrollbar component, styled after Element Plus el-scrollbar.
// Hides the native scrollbar and renders a custom track + thumb via JS.

import React, { useRef, useState, useEffect, useCallback } from 'react'

export interface ScrollbarProps {
  children: React.ReactNode
  /** Class applied to the outer container (overflow: hidden wrapper) */
  className?: string
  style?: React.CSSProperties
  /** Class applied to the inner scrollable div */
  wrapClassName?: string
  wrapStyle?: React.CSSProperties
  /** Max height applied to both outer and inner (for dropdown / modal use) */
  maxHeight?: string | number
}

export function Scrollbar({
  children,
  className = '',
  style,
  wrapClassName = '',
  wrapStyle,
  maxHeight,
}: ScrollbarProps) {
  const wrapRef = useRef<HTMLDivElement>(null)
  const [thumbH, setThumbH] = useState(0)      // thumb height as % of track
  const [thumbMove, setThumbMove] = useState(0) // translateY as % of thumb height
  const [barVisible, setBarVisible] = useState(false)
  const [dragging, setDragging] = useState(false)

  const hideTimer = useRef<ReturnType<typeof setTimeout>>()
  const dragState = useRef({ startY: 0, startScrollTop: 0 })

  // ── Recalculate thumb size + position ────────────────────────────────────
  const update = useCallback(() => {
    const el = wrapRef.current
    if (!el) return
    if (el.scrollHeight <= el.clientHeight + 1) {
      setThumbH(0)
      return
    }
    const ratio = el.clientHeight / el.scrollHeight
    setThumbH(Math.max(ratio * 100, 20))
    // Element Plus formula: move = scrollTop / clientHeight * 100
    setThumbMove((el.scrollTop / el.clientHeight) * 100)
  }, [])

  // Observe size changes (content added/removed, panel resize)
  useEffect(() => {
    const el = wrapRef.current
    if (!el) return
    update()
    const ro = new ResizeObserver(update)
    ro.observe(el)
    const mo = new MutationObserver(update)
    mo.observe(el, { childList: true, subtree: true, characterData: true })
    return () => { ro.disconnect(); mo.disconnect() }
  }, [update])

  // ── Show / auto-hide bar ──────────────────────────────────────────────────
  const showBar = useCallback(() => {
    if (thumbH === 0) return
    setBarVisible(true)
    clearTimeout(hideTimer.current)
  }, [thumbH])

  const scheduleHide = useCallback(() => {
    clearTimeout(hideTimer.current)
    hideTimer.current = setTimeout(() => {
      if (!dragging) setBarVisible(false)
    }, 1200)
  }, [dragging])

  const handleScroll = useCallback(() => {
    update()
    showBar()
    scheduleHide()
  }, [update, showBar, scheduleHide])

  // ── Drag logic ────────────────────────────────────────────────────────────
  const handleThumbDown = (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    dragState.current = {
      startY: e.clientY,
      startScrollTop: wrapRef.current?.scrollTop ?? 0,
    }
    setDragging(true)
  }

  useEffect(() => {
    if (!dragging) return
    const el = wrapRef.current
    if (!el) return

    const onMove = (e: MouseEvent) => {
      // scrollHeight / clientHeight = how many "screens" of content
      const scrollRatio = el.scrollHeight / el.clientHeight
      el.scrollTop = dragState.current.startScrollTop + (e.clientY - dragState.current.startY) * scrollRatio
    }
    const onUp = () => {
      setDragging(false)
      scheduleHide()
    }
    document.addEventListener('mousemove', onMove)
    document.addEventListener('mouseup', onUp)
    return () => {
      document.removeEventListener('mousemove', onMove)
      document.removeEventListener('mouseup', onUp)
    }
  }, [dragging, scheduleHide])

  // ── Click on track (jump to position) ────────────────────────────────────
  const handleTrackClick = (e: React.MouseEvent<HTMLDivElement>) => {
    // Ignore if click was on the thumb itself
    if ((e.target as HTMLElement).classList.contains('el-scrollbar__thumb')) return
    const el = wrapRef.current
    if (!el) return
    const rect = e.currentTarget.getBoundingClientRect()
    const clickY = e.clientY - rect.top
    const thumbPx = (thumbH / 100) * rect.height
    el.scrollTop = ((clickY - thumbPx / 2) / rect.height) * el.scrollHeight
  }

  const maxHeightVal = typeof maxHeight === 'number' ? `${maxHeight}px` : maxHeight
  const outerStyle: React.CSSProperties = {
    ...(maxHeightVal ? { maxHeight: maxHeightVal } : {}),
    ...style,
  }
  const innerStyle: React.CSSProperties = {
    ...(maxHeightVal ? { maxHeight: maxHeightVal } : {}),
    ...wrapStyle,
  }

  const isVisible = (barVisible || dragging) && thumbH > 0

  return (
    <div
      className={`el-scrollbar ${className}`}
      style={outerStyle}
      onMouseEnter={showBar}
      onMouseLeave={scheduleHide}
    >
      <div
        ref={wrapRef}
        className={`el-scrollbar__wrap ${wrapClassName}`}
        style={innerStyle}
        onScroll={handleScroll}
      >
        {children}
      </div>

      {/* Vertical track */}
      {thumbH > 0 && (
        <div
          className={`el-scrollbar__bar${isVisible ? ' is-show' : ''}`}
          onClick={handleTrackClick}
        >
          <div
            className="el-scrollbar__thumb"
            style={{ height: `${thumbH}%`, transform: `translateY(${thumbMove}%)` }}
            onMouseDown={handleThumbDown}
          />
        </div>
      )}
    </div>
  )
}

export default Scrollbar
