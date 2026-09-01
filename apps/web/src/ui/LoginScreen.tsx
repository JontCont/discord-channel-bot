import { Bot, LogIn, ShieldCheck } from 'lucide-react'
import { Link } from '@tanstack/react-router'
import { useTranslation } from 'react-i18next'
import { DisplayControls } from './DisplayControls'

export function LoginScreen() {
  const { t } = useTranslation()

  return (
    <main className="login-page">
      <DisplayControls className="login-display-controls" />
      <section className="login-panel" aria-labelledby="login-title">
        <div className="brand-mark"><Bot aria-hidden="true" /></div>
        <p className="eyebrow">{t('login.eyebrow')}</p>
        <h1 id="login-title">{t('login.title')}</h1>
        <p className="login-copy">
          {t('login.description')}
        </p>
        <a className="button primary login-button" href="/api/auth/login">
          <LogIn aria-hidden="true" /> {t('login.continue')}
        </a>
        <p className="privacy-note"><ShieldCheck aria-hidden="true" /> {t('login.secure')}</p>
        <nav className="login-legal" aria-label={t('login.legalLabel')}>
          <Link to="/privacy">{t('login.privacy')}</Link>
          <span aria-hidden="true">·</span>
          <Link to="/terms">{t('login.terms')}</Link>
        </nav>
      </section>
    </main>
  )
}