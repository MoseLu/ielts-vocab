// ── Popover Dropdown Component ────────────────────────────────────────────────
// Uses @floating-ui/react for auto-flip + arrow positioning
// Arrow aligns with trigger button center, seamlessly blends with dropdown border

import React, { useState, useRef, useEffect, useCallback } from 'react'
import {
  useFloating,
  autoUpdate,
  offset as fuiOffset,
  flip,
  shift,
  arrow as fuiArrow,
  size,
  type Placement,
  type Middleware,
} from '@floating-ui/react'

interface PopoverDropdownProps {
  /** Trigger element (button/div that opens the dropdown) */
  trigger: React.ReactNode
  /** Dropdown content */
  children: React.ReactNode
  /** Initial placement; auto-flips when space is insufficient */
  placement?: Placement
  /** Offset from trigger (px) */
  offset?: number
  /** Additional class for the dropdown panel */
  panelClassName?: string
  /** Whether the dropdown is open (controlled) */
  open?: boolean
  /** Called when open state changes */
  onOpenChange?: (open: boolean) => void
}

const PopoverDropdown: React.FC<PopoverDropdownProps> = ({
  trigger,
  children,
  placement = 'bottom',
  offset: offsetPx = 12,
  panelClassName = '',
  open: controlledOpen,
  onOpenChange,
}) => {
  const [uncontrolledOpen, setUncontrolledOpen] = useState(false)
  const arrowRef = useRef<HTMLDivElement>(null)

  const isControlled = controlledOpen !== undefined
  const isOpen = isControlled ? controlledOpen : uncontrolledOpen

  const setOpen = useCallback(
    (next: boolean) => {
      if (isControlled) {
        onOpenChange?.(next)
      } else {
        setUncontrolledOpen(next)
      }
    },
    [isControlled, onOpenChange],
  )

  // Middleware stack
  const middleware: Middleware[] = [
    fuiOffset(offsetPx),
    flip({
      boundary: document.body,
      padding: 8,
    }),
    shift({ padding: 8 }),
    fuiArrow({ element: arrowRef, padding: 8 }),
    size({
      apply({ rects, elements }) {
        // Set min-width to match trigger width for bottom/top placements
        const { width } = rects.reference
        Object.assign(elements.floating.style, {
          minWidth: `${Math.round(width)}px`,
        })
      },
    }),
  ]

  const {
    refs,
    floating,
    x,
    y,
    placement: resolvedPlacement,
    middlewareData: { arrow: arrowData },
  } = useFloating({
    placement,
    middleware,
    whileElementsMounted: autoUpdate,
    open: isOpen,
  })

  // Close on outside click
  useEffect(() => {
    if (!isOpen) return
    const handle = (e: MouseEvent) => {
      const target = e.target as Node
      if (
        refs.reference.current &&
        refs.floating.current &&
        !refs.reference.current.contains(target) &&
        !refs.floating.current.contains(target)
      ) {
        setOpen(false)
      }
    }
    document.addEventListener('pointerdown', handle)
    return () => document.removeEventListener('pointerdown', handle)
  }, [isOpen, refs.reference, refs.floating, setOpen])

  // Close on Escape
  useEffect(() => {
    if (!isOpen) return
    const handle = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('keydown', handle)
    return () => document.removeEventListener('keydown', handle)
  }, [isOpen, setOpen])

  // Derive arrow position from Floating UI's arrow data
  const arrowStyle: React.CSSProperties = arrowData
    ? {
        left: arrowData.x != null ? `${arrowData.x}px` : undefined,
        top: arrowData.y != null ? `${arrowData.y}px` : undefined,
      }
    : {}

  // Determine which side the arrow is on
  const isBottom = resolvedPlacement === 'bottom' || resolvedPlacement === 'bottom-start' || resolvedPlacement === 'bottom-end'
  const isTop = resolvedPlacement === 'top' || resolvedPlacement === 'top-start' || resolvedPlacement === 'top-end'
  const isRight = resolvedPlacement === 'right' || resolvedPlacement === 'right-start' || resolvedPlacement === 'right-end'
  const isLeft = resolvedPlacement === 'left' || resolvedPlacement === 'left-start' || resolvedPlacement === 'left-end'

  return (
    <>
      <div
        ref={refs.setReference}
        onClick={() => setOpen(!isOpen)}
        style={{ display: 'inline-block', cursor: 'pointer' }}
      >
        {trigger}
      </div>

      {isOpen && (
        <div
          ref={refs.setFloating}
          className={`popover-panel ${panelClassName}`}
          style={{
            position: 'fixed',
            left: x ?? 0,
            top: y ?? 0,
          }}
          data-placement={resolvedPlacement}
        >
          {/* Seamless arrow — positioned by Floating UI */}
          <div ref={arrowRef} className="popover-arrow" style={arrowStyle}>
            <div className="popover-arrow-inner" />
          </div>

          <div className="popover-content">{children}</div>
        </div>
      )}
    </>
  )
}

export default PopoverDropdown
