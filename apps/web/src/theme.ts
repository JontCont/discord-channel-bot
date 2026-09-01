import { useEffect, useState } from 'react'

export type Theme = 'light' | 'dark'

const STORAGE_KEY = 'channelBotTheme'
const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')

function storedTheme(): Theme | null {
  const value = localStorage.getItem(STORAGE_KEY)
  return value === 'light' || value === 'dark' ? value : null
}

function systemTheme(): Theme {
  return mediaQuery.matches ? 'dark' : 'light'
}

function applyTheme(theme: Theme) {
  document.documentElement.dataset.theme = theme
  document.documentElement.style.colorScheme = theme
}

applyTheme(storedTheme() ?? systemTheme())

export function useTheme() {
  const [theme, setThemeState] = useState<Theme>(() => storedTheme() ?? systemTheme())

  useEffect(() => {
    const handleSystemTheme = () => {
      if (storedTheme() === null) {
        const nextTheme = systemTheme()
        setThemeState(nextTheme)
        applyTheme(nextTheme)
      }
    }
    mediaQuery.addEventListener('change', handleSystemTheme)
    return () => mediaQuery.removeEventListener('change', handleSystemTheme)
  }, [])

  const setTheme = (nextTheme: Theme) => {
    localStorage.setItem(STORAGE_KEY, nextTheme)
    setThemeState(nextTheme)
    applyTheme(nextTheme)
  }

  return { theme, setTheme }
}