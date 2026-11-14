import { z } from 'zod'

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

async function apiRequest(path: string, init?: RequestInit): Promise<unknown> {
  if (import.meta.env.VITE_MOCK === 'true') {
    const { mockRequest } = await import('./mock-api')
    return mockRequest(path, init)
  }
  const response = await fetch(path, {
    ...init,
    credentials: 'include',
    headers: {
      Accept: 'application/json',
      ...(init?.body ? { 'Content-Type': 'application/json' } : {}),
      ...init?.headers,
    },
  })

  if (!response.ok) {
    let message = `Request failed with status ${response.status}`
    try {
      const body = (await response.json()) as { detail?: string; message?: string }
      message = body.detail ?? body.message ?? message
    } catch {
      // The response may intentionally have no JSON body.
    }
    throw new ApiError(message, response.status)
  }

  if (response.status === 204) return null
  return response.json()
}

const meSchema = z.object({
  id: z.string(),
  username: z.string(),
  global_name: z.string().nullish(),
  avatar_url: z.url().nullish(),
})

const guildSchema = z.object({
  id: z.string(),
  name: z.string(),
  icon: z.string().nullish(),
  icon_url: z.url().nullish(),
})

const categorySchema = z.object({
  id: z.string(),
  name: z.string(),
})

const textChannelSchema = z.object({
  id: z.string(),
  name: z.string(),
  category: z.string().nullish(),
})

const skillSchema = z.object({
  name: z.string(),
  emoji: z.string().nullish(),
  category_name: z.string(),
  role_name: z.string(),
  member_count: z.number().int(),
  invite_code: z.string(),
  direct_join: z.boolean(),
})

export const settingsSchema = z
  .object({
    auto_voice_enabled: z.boolean().default(true),
    auto_voice_trigger: z.string(),
    auto_voice_suffix: z.string(),
    auto_voice_limit: z.number().int(),
    private_rooms_enabled: z.boolean().default(true),
    private_category: z.string(),
    private_trigger: z.string(),
    private_suffix: z.string(),
    private_limit: z.number().int(),
    password_channel: z.string(),
    skills_enabled: z.boolean().default(true),
    skill_prefix: z.string(),
    skill_panel_channel: z.string(),
    skill_panel_direct_join_skills: z.array(z.string()),
    party_enabled: z.boolean().default(true),
    party_notification_channel: z.string().default('📣｜揪團通知'),
    party_panel_title: z.string(),
    party_panel_description: z.string(),
    party_panel_create_heading: z.string(),
    party_panel_create_description: z.string(),
    party_panel_list_heading: z.string(),
    party_panel_list_description: z.string(),
    party_panel_create_label: z.string(),
    party_panel_list_label: z.string(),
    skill_panel_title: z.string(),
    skill_panel_description: z.string(),
    skill_panel_footer: z.string(),
    leveling_enabled: z.boolean().default(true),
    xp_per_message_min: z.number().int(),
    xp_per_message_max: z.number().int(),
    xp_message_cooldown: z.number().int(),
    xp_per_voice_tick: z.number().int(),
    xp_voice_interval: z.number().int(),
    xp_daily_base: z.number().int(),
    levelup_channel: z.string(),
    level_roles: z.array(z.tuple([z.number().int(), z.string(), z.number().int()])),
  })
  .strip()

export type User = z.infer<typeof meSchema>
export type Guild = z.infer<typeof guildSchema>
export type GuildCategory = z.infer<typeof categorySchema>
export type GuildTextChannel = z.infer<typeof textChannelSchema>
export type GuildSkill = z.infer<typeof skillSchema>
export type GuildSettings = z.infer<typeof settingsSchema>

function unwrap<T>(data: unknown, key: string, schema: z.ZodType<T>): T {
  if (typeof data === 'object' && data !== null && key in data) {
    return schema.parse((data as Record<string, unknown>)[key])
  }
  return schema.parse(data)
}

export async function getMe(): Promise<User> {
  return unwrap(await apiRequest('/api/me'), 'user', meSchema)
}

export async function getGuilds(): Promise<Guild[]> {
  return unwrap(await apiRequest('/api/guilds'), 'guilds', z.array(guildSchema))
}

export async function getGuildSettings(guildId: string): Promise<GuildSettings> {
  return unwrap(
    await apiRequest(`/api/guilds/${encodeURIComponent(guildId)}/settings`),
    'settings',
    settingsSchema,
  )
}

export async function getGuildCategories(guildId: string): Promise<GuildCategory[]> {
  return unwrap(
    await apiRequest(`/api/guilds/${encodeURIComponent(guildId)}/categories`),
    'categories',
    z.array(categorySchema),
  )
}

export async function getGuildChannels(guildId: string): Promise<GuildTextChannel[]> {
  return unwrap(
    await apiRequest(`/api/guilds/${encodeURIComponent(guildId)}/channels`),
    'channels',
    z.array(textChannelSchema),
  )
}

export async function getGuildSkills(guildId: string): Promise<GuildSkill[]> {
  return unwrap(
    await apiRequest(`/api/guilds/${encodeURIComponent(guildId)}/skills`),
    'skills',
    z.array(skillSchema),
  )
}

export async function createGuildSkill(
  guildId: string,
  payload: { name: string; emoji?: string },
): Promise<GuildSkill> {
  return unwrap(
    await apiRequest(`/api/guilds/${encodeURIComponent(guildId)}/skills`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
    'skill',
    skillSchema,
  )
}

export async function regenerateGuildSkillCode(
  guildId: string,
  skillName: string,
): Promise<string> {
  const data = await apiRequest(
    `/api/guilds/${encodeURIComponent(guildId)}/skills/${encodeURIComponent(skillName)}/regenerate-code`,
    { method: 'POST' },
  )
  return unwrap(data, 'invite_code', z.string())
}

export async function deleteGuildSkill(
  guildId: string,
  skillName: string,
): Promise<void> {
  await apiRequest(
    `/api/guilds/${encodeURIComponent(guildId)}/skills/${encodeURIComponent(skillName)}`,
    { method: 'DELETE' },
  )
}

export async function updateGuildSettings(
  guildId: string,
  settings: GuildSettings,
): Promise<GuildSettings> {
  const data = await apiRequest(
    `/api/guilds/${encodeURIComponent(guildId)}/settings`,
    { method: 'PUT', body: JSON.stringify(settings) },
  )
  return unwrap(data, 'settings', settingsSchema)
}

export function guildIconUrl(guild: Guild): string | undefined {
  if (guild.icon_url) return guild.icon_url
  if (!guild.icon) return undefined
  return `https://cdn.discordapp.com/icons/${guild.id}/${guild.icon}.webp?size=96`
}