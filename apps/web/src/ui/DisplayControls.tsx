import { Moon, Sun } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useTheme } from '../theme'
import { LanguageSwitcher } from './LanguageSwitcher'

export function DisplayControls({ className = '' }: { className?: string }) {
  const { t } = useTranslation()
  const { theme, setTheme } = useTheme()
  const nextTheme = theme === 'dark' ? 'light' : 'dark'
  const label = t(`theme.${nextTheme}`)

  return (
    <div className={`display-controls ${className}`.trim()}>
      <LanguageSwitcher />
      <button
        className="icon-button theme-toggle"
        type="button"
        aria-label={label}
        title={label}
        onClick={() => setTheme(nextTheme)}
      >
        {theme === 'dark' ? <Sun aria-hidden="true" /> : <Moon aria-hidden="true" />}
      </button>
    </div>
  )
}