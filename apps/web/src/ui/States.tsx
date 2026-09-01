import { AlertCircle, Bot, Inbox, LoaderCircle, RefreshCw } from 'lucide-react'
import { Link } from '@tanstack/react-router'

export function LoadingState({ label = 'Loading dashboard' }: { label?: string }) {
  return (
    <div className="state" role="status">
      <LoaderCircle className="spin" aria-hidden="true" />
      <p>{label}</p>
    </div>
  )
}

export function ErrorState({
  message,
  onRetry,
}: {
  message: string
  onRetry?: () => void
}) {
  return (
    <div className="state state-error" role="alert">
      <AlertCircle aria-hidden="true" />
      <div>
        <strong>Something went wrong</strong>
        <p>{message}</p>
      </div>
      {onRetry && (
        <button className="button secondary" type="button" onClick={onRetry}>
          <RefreshCw aria-hidden="true" /> Retry
        </button>
      )}
    </div>
  )
}

export function EmptyState() {
  return (
    <div className="state">
      <Inbox aria-hidden="true" />
      <div>
        <strong>No manageable servers</strong>
        <p>Servers where you can manage the bot will appear here.</p>
      </div>
      <a className="button primary" href="/api/bot/invite">
        <Bot aria-hidden="true" /> Invite bot
      </a>
    </div>
  )
}

export function NotFound() {
  return (
    <main className="center-page">
      <div className="state">
        <AlertCircle aria-hidden="true" />
        <div>
          <strong>Page not found</strong>
          <p>The requested dashboard page does not exist.</p>
        </div>
        <Link className="button secondary" to="/guilds">Back to servers</Link>
      </div>
    </main>
  )
}