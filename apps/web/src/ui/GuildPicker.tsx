import { useQuery } from '@tanstack/react-query'
import { Link } from '@tanstack/react-router'
import { ChevronRight, Server } from 'lucide-react'
import { getGuilds, guildIconUrl } from '../api'
import { EmptyState, ErrorState, LoadingState } from './States'

export function GuildPicker() {
  const guilds = useQuery({ queryKey: ['guilds'], queryFn: getGuilds })

  return (
    <main className="page page-narrow">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Server access</p>
          <h1>Select a server</h1>
          <p>Choose where you want to update bot settings.</p>
        </div>
      </div>
      {guilds.isLoading && <LoadingState label="Loading servers" />}
      {guilds.isError && <ErrorState message={guilds.error.message} onRetry={() => void guilds.refetch()} />}
      {guilds.data?.length === 0 && <EmptyState />}
      {guilds.data && guilds.data.length > 0 && (
        <div className="guild-list" aria-label="Available Discord servers">
          {guilds.data.map((guild) => {
            const iconUrl = guildIconUrl(guild)
            return (
              <Link key={guild.id} className="guild-row" to="/guilds/$guildId/settings" params={{ guildId: guild.id }}>
                {iconUrl ? <img src={iconUrl} alt="" /> : <span className="guild-fallback"><Server aria-hidden="true" /></span>}
                <span className="guild-name">{guild.name}</span>
                <span className="guild-action">Configure <ChevronRight aria-hidden="true" /></span>
              </Link>
            )
          })}
        </div>
      )}
    </main>
  )
}