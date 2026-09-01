import { useQuery } from '@tanstack/react-query'
import { Link, Outlet, useNavigate } from '@tanstack/react-router'
import { Bot, LogOut } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { ApiError, getMe } from '../api'
import { ErrorState, LoadingState } from './States'
import { DisplayControls } from './DisplayControls'

export function AuthenticatedLayout() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [isSigningOut, setIsSigningOut] = useState(false)
  const me = useQuery({ queryKey: ['me'], queryFn: getMe })

  const signOut = async () => {
    setIsSigningOut(true)
    try {
      await fetch('/api/auth/logout', {
        method: 'POST',
        credentials: 'include',
      })
    } finally {
      await navigate({ to: '/login', replace: true })
      setIsSigningOut(false)
    }
  }

  if (me.isLoading) return <main className="center-page"><LoadingState label={t('auth.starting')} /></main>
  if (me.error instanceof ApiError && me.error.status === 401) {
    void navigate({ to: '/login', replace: true })
    return <main className="center-page"><LoadingState label={t('auth.opening')} /></main>
  }
  if (me.isError) {
    return <main className="center-page"><ErrorState message={me.error.message} onRetry={() => void me.refetch()} /></main>
  }

  const user = me.data!
  const displayName = user.global_name ?? user.username

  return (
    <div className="app-shell">
      <header className="topbar">
        <Link className="brand" to="/guilds" aria-label={t('common.productHome')}>
          <span className="brand-mark small"><Bot aria-hidden="true" /></span>
          <span>Channel Bot</span>
        </Link>
        <div className="account">
          <DisplayControls />
          {user.avatar_url ? <img src={user.avatar_url} alt="" /> : <span className="avatar-fallback">{displayName.charAt(0)}</span>}
          <span className="account-name">{displayName}</span>
          <button
            className="icon-button"
            type="button"
            aria-label={t('auth.signOut')}
            title={t('auth.signOut')}
            disabled={isSigningOut}
            onClick={() => void signOut()}
          >
            <LogOut aria-hidden="true" />
          </button>
        </div>
      </header>
      <Outlet />
    </div>
  )
}