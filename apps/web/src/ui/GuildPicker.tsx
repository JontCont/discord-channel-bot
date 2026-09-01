import { useQuery } from '@tanstack/react-query'
import { Link } from '@tanstack/react-router'
import { ChevronRight, Server } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { getGuilds, guildIconUrl } from '../api'
import { EmptyState, ErrorState, LoadingState } from './States'

export function GuildPicker() {
  const { t } = useTranslation()
  const guilds = useQuery({ queryKey: ['guilds'], queryFn: getGuilds })

  return (
    <main className="page page-narrow">
      <div className="page-heading">
        <div>
          <p className="eyebrow">{t('guilds.eyebrow')}</p>
          <h1>{t('guilds.title')}</h1>
          <p>{t('guilds.description')}</p>
        </div>
      </div>
      {guilds.isLoading && <LoadingState label={t('guilds.loading')} />}
      {guilds.isError && <ErrorState message={guilds.error.message} onRetry={() => void guilds.refetch()} />}
      {guilds.data?.length === 0 && <EmptyState />}
      {guilds.data && guilds.data.length > 0 && (
        <div className="guild-list" aria-label={t('guilds.listLabel')}>
          {guilds.data.map((guild) => {
            const iconUrl = guildIconUrl(guild)
            return (
              <Link key={guild.id} className="guild-row" to="/guilds/$guildId/settings" params={{ guildId: guild.id }}>
                {iconUrl ? <img src={iconUrl} alt="" /> : <span className="guild-fallback"><Server aria-hidden="true" /></span>}
                <span className="guild-name">{guild.name}</span>
                <span className="guild-action">{t('guilds.configure')} <ChevronRight aria-hidden="true" /></span>
              </Link>
            )
          })}
        </div>
      )}
    </main>
  )
}