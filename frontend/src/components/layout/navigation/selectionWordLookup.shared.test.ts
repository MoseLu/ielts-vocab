import { describe, expect, it } from 'vitest'
import {
  resolveSelectionLookupPosition,
  type SelectionLookupAnchorRect,
} from './selectionWordLookup.shared'

function makeAnchorRect(overrides: Partial<SelectionLookupAnchorRect> = {}): SelectionLookupAnchorRect {
  return {
    x: 480,
    y: 220,
    top: 220,
    right: 560,
    bottom: 248,
    left: 480,
    width: 80,
    height: 28,
    ...overrides,
  }
}

describe('resolveSelectionLookupPosition', () => {
  it('places the lookup card below the selection with a right-side bias by default', () => {
    expect(resolveSelectionLookupPosition(
      makeAnchorRect(),
      { width: 320, height: 220 },
      { width: 1280, height: 900 },
    )).toEqual({
      left: 472,
      top: 256,
    })
  })

  it('flips above the selection when there is not enough room below', () => {
    expect(resolveSelectionLookupPosition(
      makeAnchorRect({ bottom: 820, top: 792, y: 792 }),
      { width: 320, height: 220 },
      { width: 1280, height: 900 },
    )).toEqual({
      left: 472,
      top: 564,
    })
  })
})
