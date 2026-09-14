// ── Popover Dropdown Component ────────────────────────────────────────────────
// Matches Element Plus el-dropdown behavior:
//   - Portal-rendered to body (avoids stacking context issues)
//   - Open/close fade+slide animation (both directions)
//   - Clicking any item inside automatically closes the dropdown
//   - Arrow uses 1px border technique matching el-popper style
//   - Auto-flip when space is insufficient (@floating-ui)

import React, { useState, useRef, useEffect, useCallback, useId, isValidElement, cloneElement } from 'react'
import { createPortal } from 'react-dom'
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

const CLOSE_DURATION = 150 // ms — must match CSS animation duration
type PopoverTriggerProps = React.HTMLAttributes<HTMLElement> & React.RefAttributes<HTMLElement>

function mergeRefs<T>(...refs: Array<React.Ref<T> | undefined>) {
  return (node: T | null) => {
    refs.forEach((ref) => {
      if (typeof ref === 'function') {
        ref(node)
      } else if (ref && typeof ref === 'object') {
        ;(ref as React.MutableRefObject<T | null>).current = node
      }
    })
  }
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
  // displayPanel: whether the DOM element should exist (includes closing animation)
  const [displayPanel, setDisplayPanel] = useState(false)
  // isClosing: whether the closing animation is playing
  const [isClosing, setIsClosing] = useState(false)
  const closeTimerRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)
  const arrowRef = useRef<HTMLDivElement>(null)
  const panelRef = useRef<HTMLDivElement | null>(null)
  const panelId = useId()

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

  // Sync display state with open state (adds close animation delay)
  useEffect(() => {
    if (isOpen) {
      clearTimeout(closeTimerRef.current)
      setIsClosing(false)
      setDisplayPanel(true)
    } else if (displayPanel) {
      setIsClosing(true)
      closeTimerRef.current = setTimeout(() => {
        setDisplayPanel(false)
        setIsClosing(false)
      }, CLOSE_DURATION)
    }
    return () => clearTimeout(closeTimerRef.current)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen])

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
      apply({ rects }) {
        panelRef.current?.style.setProperty('--popover-min-width', `${Math.round(rects.reference.width)}px`)
      },
    }),
  ]

  const {
    refs,
    x,
    y,
    strategy,
    placement: resolvedPlacement,
    middlewareData: { arrow: arrowData },
  } = useFloating({
    placement,
    middleware,
    whileElementsMounted: autoUpdate,
    open: displayPanel,
    strategy: 'fixed',
  })

  // Close on outside click
  useEffect(() => {
    if (!displayPanel) return
    const handle = (e: MouseEvent) => {
      const target = e.target as Node
      const reference = refs.reference.current
      const floating = refs.floating.current
      const targetWithinReference = reference instanceof Element && reference.contains(target)
      if (
        reference &&
        floating &&
        !targetWithinReference &&
        !floating.contains(target)
      ) {
        setOpen(false)
      }
    }
    document.addEventListener('pointerdown', handle)
    return () => document.removeEventListener('pointerdown', handle)
  }, [displayPanel, refs.reference, refs.floating, setOpen])

  // Close on Escape
  useEffect(() => {
    if (!displayPanel) return
    const handle = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('keydown', handle)
    return () => document.removeEventListener('keydown', handle)
  }, [displayPanel, setOpen])

  useEffect(() => {
    const arrow = arrowRef.current
    if (!arrow) return
    if (arrowData?.x != null) arrow.style.left = `${arrowData.x}px`
    else arrow.style.removeProperty('left')
    if (arrowData?.y != null) arrow.style.top = `${arrowData.y}px`
    else arrow.style.removeProperty('top')
  }, [arrowData])

  const floatingStyle =
    x != null && y != null
      ? { position: strategy, left: x, top: y }
      : { position: strategy, visibility: 'hidden' as const }

  const toggleOpen = useCallback(() => {
    setOpen(!isOpen)
  }, [isOpen, setOpen])

  const triggerElement = isValidElement<PopoverTriggerProps>(trigger) ? trigger : null
  const triggerNode = triggerElement
    ? cloneElement(triggerElement, {
        ref: mergeRefs(
          triggerElement.props.ref,
          refs.setReference,
        ),
        onClick: (event: React.MouseEvent<HTMLElement>) => {
          const originalOnClick = triggerElement.props.onClick
          originalOnClick?.(event)
          if (!event.defaultPrevented) {
            toggleOpen()
          }
        },
        'aria-expanded': isOpen,
        'aria-controls': displayPanel ? panelId : undefined,
      })
    : (
        <button
          type="button"
          ref={refs.setReference}
          onClick={toggleOpen}
          className="popover-trigger"
          aria-expanded={isOpen}
          aria-controls={displayPanel ? panelId : undefined}
        >
          {trigger}
        </button>
      )

  const panel = displayPanel
    ? createPortal(
        <div
          id={panelId}
          ref={(node) => {
            refs.setFloating(node)
            panelRef.current = node
          }}
          className={`popover-panel ${panelClassName} ${isClosing ? 'popover-closing' : ''}`}
          data-placement={resolvedPlacement}
          style={floatingStyle}
          // Clicking anywhere inside the panel closes the dropdown.
          // Individual items that should NOT auto-close can call e.stopPropagation().
          onClick={() => setOpen(false)}
        >
          {/* Arrow — Element Plus single-element technique */}
          <div ref={arrowRef} className="popover-arrow" />

          <div className="popover-content">
            {children}
          </div>
        </div>,
        document.body,
      )
    : null

  return (
    <>
      {triggerNode}
      {panel}
    </>
  )
}

export default PopoverDropdown
