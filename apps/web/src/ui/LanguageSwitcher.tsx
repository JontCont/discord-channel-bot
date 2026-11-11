import { Languages } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { supportedLanguages, type SupportedLanguage } from '../i18n'

const languageNames: Record<SupportedLanguage, string> = {
  en: 'English',
  'zh-Hant': '繁體中文',
  ja: '日本語',
}

export function LanguageSwitcher({ className = '' }: { className?: string }) {
  const { i18n, t } = useTranslation()
  const currentLanguage = supportedLanguages.find(
    (language) => i18n.resolvedLanguage === language,
  ) ?? 'en'

  return (
    <label className={`language-switcher ${className}`.trim()}>
      <Languages aria-hidden="true" />
      <span className="sr-only">{t('common.language')}</span>
      <select
        aria-label={t('common.language')}
        value={currentLanguage}
        onChange={(event) => void i18n.changeLanguage(event.target.value)}
      >
        {supportedLanguages.map((language) => (
          <option key={language} value={language}>{languageNames[language]}</option>
        ))}
      </select>
    </label>
  )
}