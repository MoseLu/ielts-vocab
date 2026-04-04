import React from 'react'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Routes, Route, useLocation } from 'react-router-dom'
import LeftSidebar from './LeftSidebar'
import BottomNav from './BottomNav'

function LocationProbe() {
  const location = useLocation()
  return <div data-testid="location-probe">{location.pathname}</div>
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
})
