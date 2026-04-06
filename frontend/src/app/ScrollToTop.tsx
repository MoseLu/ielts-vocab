import { useEffect } from 'react'
import { useLocation, useNavigationType } from 'react-router-dom'

export function ScrollToTop() {
  const { pathname } = useLocation()
  const navType = useNavigationType()

  useEffect(() => {
    if (navType === 'POP') return

    const scrollTargets = document.querySelectorAll<HTMLElement>(
      '.page__scroll, .page-content, .page-shell-body, .stats-page-scroll, .errors-content-scroll, .journal-doc-list, .journal-doc-body, .journal-doc-main-scroll',
    )

    if (scrollTargets.length > 0) {
      scrollTargets.forEach(target =>
        target.scrollTo({ top: 0, left: 0, behavior: 'instant' }),
      )
      return
    }

    window.scrollTo({ top: 0, left: 0, behavior: 'instant' })
  }, [pathname, navType])

  return null
}
