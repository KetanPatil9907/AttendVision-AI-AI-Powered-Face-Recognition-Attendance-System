import { Component } from 'react'
import { Button } from './ui.jsx'

/** Catches render-time crashes so one broken view never blanks the whole app. */
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { error: null }
  }

  static getDerivedStateFromError(error) {
    return { error }
  }

  componentDidCatch(error, info) {
    console.error('Unhandled UI error:', error, info)
  }

  render() {
    if (this.state.error) {
      return (
        <div className="m-6 max-w-xl rounded-xl border border-red-200 bg-red-50 p-6 text-sm text-red-700">
          <p className="mb-1 font-semibold">Something went wrong in the interface.</p>
          <p className="mb-4 break-words text-red-600">{String(this.state.error?.message || this.state.error)}</p>
          <div className="flex gap-2">
            <Button variant="secondary" onClick={() => this.setState({ error: null })}>
              Try again
            </Button>
            <button
              className="rounded-lg px-3 py-2 font-medium text-red-700 hover:bg-red-100"
              onClick={() => window.location.assign('/')}
            >
              Go to dashboard
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}
