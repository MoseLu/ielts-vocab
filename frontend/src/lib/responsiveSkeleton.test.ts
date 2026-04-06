import {
  calculateAutoFitColumns,
  calculateChapterModalSkeletonCount,
  calculatePageSkeletonCount,
  estimateMainContentWidth,
  resolveChapterGridColumns,
} from './responsiveSkeleton'

describe('responsiveSkeleton', () => {
  it('estimates the main content width from the desktop shell layout', () => {
    expect(estimateMainContentWidth(1440)).toBe(1260)
    expect(estimateMainContentWidth(768)).toBe(748)
  })

  it('derives auto-fit grid columns from width, card min width, and gap', () => {
    expect(calculateAutoFitColumns({ containerWidth: 1260, minColumnWidth: 260, gap: 10 })).toBe(4)
    expect(calculateAutoFitColumns({ containerWidth: 1620, minColumnWidth: 220, gap: 10 })).toBe(7)
  })

  it('uses the estimated page width to produce responsive page skeleton counts', () => {
    expect(calculatePageSkeletonCount({ viewportWidth: 1800, minColumnWidth: 260, gap: 10 })).toBe(6)
    expect(calculatePageSkeletonCount({ viewportWidth: 1800, minColumnWidth: 220, gap: 10 })).toBe(7)
  })

  it('matches the chapter modal breakpoint columns used by the stylesheet', () => {
    expect(resolveChapterGridColumns(1200)).toBe(4)
    expect(resolveChapterGridColumns(900)).toBe(3)
    expect(resolveChapterGridColumns(680)).toBe(2)
  })

  it('calculates chapter skeleton count from first-screen columns and visible rows', () => {
    expect(
      calculateChapterModalSkeletonCount({
        viewportWidth: 1440,
        bodyHeight: 640,
        rowMinHeight: 156,
        gap: 10,
        maxRows: 3,
      }),
    ).toBe(12)

    expect(
      calculateChapterModalSkeletonCount({
        viewportWidth: 640,
        bodyHeight: 640,
        rowMinHeight: 156,
        gap: 10,
        maxRows: 3,
      }),
    ).toBe(6)
  })
})
