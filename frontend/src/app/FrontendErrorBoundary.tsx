import type { ErrorInfo, ReactNode } from 'react'
import { Component } from 'react'
import { reportReactError } from '../lib/errorReporting'

interface FrontendErrorBoundaryProps {
  children: ReactNode
}

interface FrontendErrorBoundaryState {
  hasError: boolean
}

export class FrontendErrorBoundary extends Component<
  FrontendErrorBoundaryProps,
  FrontendErrorBoundaryState
> {
  state: FrontendErrorBoundaryState = { hasError: false }

  static getDerivedStateFromError(): FrontendErrorBoundaryState {
    return { hasError: true }
  }

  componentDidCatch(error: unknown, info: ErrorInfo): void {
    reportReactError(error, info.componentStack ?? undefined)
  }

  render() {
    if (this.state.hasError) {
      return <div className="loading-fullscreen">页面加载失败，请刷新重试</div>
    }
    return this.props.children
  }
}
