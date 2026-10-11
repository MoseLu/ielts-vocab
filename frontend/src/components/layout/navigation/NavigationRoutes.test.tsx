import React from 'react'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Routes, Route, useLocation } from 'react-router-dom'
import LeftSidebar from './LeftSidebar'
import BottomNav, { assertSafeBottomNavIcon } from './BottomNav'

function LocationProbe() {
  const location = useLocation()
  return <div data-testid="location-probe">{`${location.pathname}${location.search}`}</div>
}

function renderWithRouter(ui: React.ReactNode, initialPath = '/stats') {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      {ui}
      <Routes>
        <Route path="*" element={<LocationProbe />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('navigation entry routes', () => {
  it('rejects unsafe bottom navigation SVG assets', () => {
    expect(() => assertSafeBottomNavIcon('<svg><script>alert(1)</script></svg>')).toThrow(/Unsafe/)
    expect(() => assertSafeBottomNavIcon('<svg><path onclick="alert(1)" /></svg>')).toThrow(/Unsafe/)
    expect(() => assertSafeBottomNavIcon('<svg><foreignObject /></svg>')).toThrow(/Unsafe/)
  })

  it('locks required bottom navigation SVG animation hooks', () => {
    expect(() => assertSafeBottomNavIcon('<svg><path id="home-door" /></svg>', ['home-door'])).not.toThrow()
    expect(() => assertSafeBottomNavIcon('<svg><path /></svg>', ['home-door'])).toThrow(/home-door/)
  })

  it('keeps exams out of the left sidebar navigation', () => {
    renderWithRouter(<LeftSidebar />)

    expect(screen.queryByRole('button', { name: '真题' })).not.toBeInTheDocument()
  })

  it('routes the left sidebar home item to the study center', async () => {
    const user = userEvent.setup()
    renderWithRouter(<LeftSidebar />)

    await user.click(screen.getByRole('button', { name: '首页' }))

    expect(screen.getByTestId('location-probe')).toHaveTextContent('/plan')
  })

  it('routes the bottom nav home item to the study center', async () => {
    const user = userEvent.setup()
    renderWithRouter(<BottomNav />)

    await user.click(screen.getByRole('button', { name: '首页' }))

    expect(screen.getByTestId('location-probe')).toHaveTextContent('/plan')
  })

  it('marks only the study center item active on the plan route', () => {
    renderWithRouter(<BottomNav />, '/plan')

    const home = screen.getByRole('button', { name: '首页' })
    const practice = screen.getByRole('button', { name: '练习' })

    expect(home).toHaveClass('active')
    expect(home).toHaveAttribute('aria-current', 'page')
    expect(practice).not.toHaveClass('active')
    expect(practice).not.toHaveAttribute('aria-current')
    expect(practice).not.toHaveClass('bottom-nav-item--primary')
  })

  it('marks practice active only on the practice route family', () => {
    renderWithRouter(<BottomNav />, '/practice/confusable')

    const home = screen.getByRole('button', { name: '首页' })
    const practice = screen.getByRole('button', { name: '练习' })

    expect(practice).toHaveClass('active')
    expect(practice).toHaveAttribute('aria-current', 'page')
    expect(home).not.toHaveClass('active')
  })

  it('marks practice active on the base practice route', () => {
    renderWithRouter(<BottomNav />, '/practice')

    const practice = screen.getByRole('button', { name: '练习' })
    const stats = screen.getByRole('button', { name: '数据' })

    expect(practice).toHaveClass('active')
    expect(practice).toHaveAttribute('aria-current', 'page')
    expect(stats).not.toHaveClass('active')
  })

  it('hides the left sidebar game item while five-dimensional mode is closed', () => {
    renderWithRouter(<LeftSidebar />)

    expect(screen.queryByRole('button', { name: '五维闯关' })).not.toBeInTheDocument()
  })

  it('routes the bottom nav practice item to the foundational practice page', async () => {
    const user = userEvent.setup()
    renderWithRouter(<BottomNav />)

    await user.click(screen.getByRole('button', { name: '练习' }))

    expect(screen.getByTestId('location-probe')).toHaveTextContent('/practice?review=due')
  })
})
