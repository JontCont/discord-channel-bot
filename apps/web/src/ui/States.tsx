import { AlertCircle, Bot, Inbox, LoaderCircle, RefreshCw } from 'lucide-react'
import { Link } from '@tanstack/react-router'
import { useTranslation } from 'react-i18next'

export function LoadingState({ label }: { label?: string }) {
  const { t } = useTranslation()
  return (
    <div className="state" role="status">
      <LoaderCircle className="spin" aria-hidden="true" />
      <p>{label ?? t('common.loading')}</p>
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
  const { t } = useTranslation()
  return (
    <div className="state state-error" role="alert">
      <AlertCircle aria-hidden="true" />
      <div>
        <strong>{t('states.errorTitle')}</strong>
        <p>{message}</p>
      </div>
      {onRetry && (
        <button className="button secondary" type="button" onClick={onRetry}>
          <RefreshCw aria-hidden="true" /> {t('common.retry')}
        </button>
      )}
    </div>
  )
}

export function EmptyState() {
  const { t } = useTranslation()
  return (
    <div className="state">
      <Inbox aria-hidden="true" />
      <div>
        <strong>{t('states.emptyTitle')}</strong>
        <p>{t('states.emptyDescription')}</p>
      </div>
      <a className="button primary" href="/api/bot/invite">
        <Bot aria-hidden="true" /> {t('states.invite')}
      </a>
    </div>
  )
}

export function NotFound() {
  const { t } = useTranslation()
  return (
    <main className="center-page">
      <div className="state">
        <AlertCircle aria-hidden="true" />
        <div>
          <strong>{t('states.notFoundTitle')}</strong>
          <p>{t('states.notFoundDescription')}</p>
        </div>
        <Link className="button secondary" to="/guilds">{t('states.backToServers')}</Link>
      </div>
    </main>
  )
}