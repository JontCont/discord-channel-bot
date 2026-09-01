import { Link } from '@tanstack/react-router'
import { Bot } from 'lucide-react'
import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { DisplayControls } from './DisplayControls'

function LegalPage({ title, children }: { title: string; children: ReactNode }) {
  const { t } = useTranslation()
  return (
    <div className="legal-shell">
      <header className="legal-topbar">
        <Link className="brand" to="/login" aria-label={t('common.productHome')}>
          <span className="brand-mark small"><Bot aria-hidden="true" /></span>
          <span>Channel Bot</span>
        </Link>
        <div className="legal-actions">
          <nav className="legal-nav" aria-label={t('legal.navigation')}>
            <Link to="/privacy" activeProps={{ 'aria-current': 'page' }}>{t('legal.privacyNav')}</Link>
            <Link to="/terms" activeProps={{ 'aria-current': 'page' }}>{t('legal.termsNav')}</Link>
          </nav>
          <DisplayControls />
        </div>
      </header>
      <main className="legal-page">
        <p className="eyebrow">Channel Bot</p>
        <h1>{title}</h1>
        <p className="legal-date">{t('legal.effectiveDate', { date: t('legal.date') })}</p>
        <div className="legal-content">{children}</div>
      </main>
    </div>
  )
}

export function PrivacyPolicyPage() {
  const { t } = useTranslation()
  return (
    <LegalPage title={t('legal.privacy.title')}>
      <section>
        <h2>{t('legal.privacy.overviewTitle')}</h2>
        <p>{t('legal.privacy.overviewBody')}</p>
      </section>
      <section>
        <h2>{t('legal.privacy.informationTitle')}</h2>
        <ul>
          <li><strong>{t('legal.privacy.accountLabel')}</strong> {t('legal.privacy.accountBody')}</li>
          <li><strong>{t('legal.privacy.serverLabel')}</strong> {t('legal.privacy.serverBody')}</li>
          <li><strong>{t('legal.privacy.activityLabel')}</strong> {t('legal.privacy.activityBody')}</li>
          <li><strong>{t('legal.privacy.configurationLabel')}</strong> {t('legal.privacy.configurationBody')}</li>
          <li><strong>{t('legal.privacy.authenticationLabel')}</strong> {t('legal.privacy.authenticationBody')}</li>
        </ul>
        <p>{t('legal.privacy.noMessages')}</p>
      </section>
      <section>
        <h2>{t('legal.privacy.useTitle')}</h2>
        <p>{t('legal.privacy.useBody')}</p>
      </section>
      <section>
        <h2>{t('legal.privacy.sharingTitle')}</h2>
        <p>{t('legal.privacy.sharingBody')}</p>
      </section>
      <section>
        <h2>{t('legal.privacy.storageTitle')}</h2>
        <p>{t('legal.privacy.storageBody')}</p>
      </section>
      <section>
        <h2>{t('legal.privacy.securityTitle')}</h2>
        <p>{t('legal.privacy.securityBody')}</p>
      </section>
      <section>
        <h2>{t('legal.privacy.choicesTitle')}</h2>
        <p>{t('legal.privacy.choicesBody')}</p>
      </section>
      <section>
        <h2>{t('legal.privacy.changesTitle')}</h2>
        <p>{t('legal.privacy.changesBody')}</p>
      </section>
    </LegalPage>
  )
}

export function TermsOfServicePage() {
  const { t } = useTranslation()
  return (
    <LegalPage title={t('legal.terms.title')}>
      <section>
        <h2>{t('legal.terms.acceptanceTitle')}</h2>
        <p>{t('legal.terms.acceptanceBody')}</p>
      </section>
      <section>
        <h2>{t('legal.terms.eligibilityTitle')}</h2>
        <p>{t('legal.terms.eligibilityBody')}</p>
      </section>
      <section>
        <h2>{t('legal.terms.acceptableTitle')}</h2>
        <p>{t('legal.terms.acceptableIntro')}</p>
        <ul>
          <li>{t('legal.terms.acceptableOne')}</li>
          <li>{t('legal.terms.acceptableTwo')}</li>
          <li>{t('legal.terms.acceptableThree')}</li>
          <li>{t('legal.terms.acceptableFour')}</li>
        </ul>
      </section>
      <section>
        <h2>{t('legal.terms.configurationTitle')}</h2>
        <p>{t('legal.terms.configurationBody')}</p>
      </section>
      <section>
        <h2>{t('legal.terms.availabilityTitle')}</h2>
        <p>{t('legal.terms.availabilityBody')}</p>
      </section>
      <section>
        <h2>{t('legal.terms.terminationTitle')}</h2>
        <p>{t('legal.terms.terminationBody')}</p>
      </section>
      <section>
        <h2>{t('legal.terms.liabilityTitle')}</h2>
        <p>{t('legal.terms.liabilityBody')}</p>
      </section>
      <section>
        <h2>{t('legal.terms.privacyTitle')}</h2>
        <p>
          {t('legal.terms.privacyBefore')} <Link to="/privacy">{t('legal.privacy.title')}</Link> {t('legal.terms.privacyAfter')}
        </p>
      </section>
      <section>
        <h2>{t('legal.terms.contactTitle')}</h2>
        <p>{t('legal.terms.contactBody')}</p>
      </section>
    </LegalPage>
  )
}