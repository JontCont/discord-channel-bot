// Mock backend for `pnpm run web:mock`. Active only in Vite `mock` mode; no login or API server needed.
import { ApiError, type GuildSettings, type GuildSkill } from './api'
import { MOCK_GUILD_ID } from './mock-constants'

const user = {
  id: '200000000000000001',
  username: 'mock-admin',
  global_name: 'Mock 管理員',
  avatar_url: null,
}

const guilds = [
  { id: MOCK_GUILD_ID, name: '喵湯測試伺服器 (Mock)', icon: null, icon_url: null },
  { id: '100000000000000002', name: '第二個 Mock 伺服器', icon: null, icon_url: null },
]

const categories = [
  { id: '300000000000000001', name: '🎮｜遊戲揪團' },
  { id: '300000000000000002', name: '🎲｜桌遊' },
  { id: '300000000000000003', name: '💬｜閒聊' },
]

const channels = [
  { id: '400000000000000001', name: '📣｜揪團通知', category: '一般' },
  { id: '400000000000000002', name: '🎯｜社群入口', category: '一般' },
  { id: '400000000000000003', name: '🎮｜遊戲大廳', category: '🎮｜遊戲揪團' },
  { id: '400000000000000004', name: '🎲｜桌遊討論', category: '🎲｜桌遊' },
  { id: '400000000000000005', name: '💬｜綜合閒聊', category: '💬｜閒聊' },
]

function defaultSettings(): GuildSettings {
  return {
    auto_voice_enabled: true,
    auto_voice_trigger: '➕ 建立語音頻道',
    auto_voice_suffix: '語音房',
    auto_voice_limit: 6,
    private_rooms_enabled: true,
    private_category: '🔒 私人湯',
    private_trigger: '➕ 開設私人包廂',
    private_suffix: '的包廂',
    private_limit: 4,
    password_channel: '🔑｜輸入密碼',
    skills_enabled: true,
    skill_prefix: '湯技：',
    skill_panel_channel: '🎯｜社群入口',
    skill_panel_direct_join_skills: ['鍛造術', '遊戲術', '墨繪術'],
    party_enabled: true,
    party_notification_channel: '400000000000000001',
    party_panel_title: '🎯 社群入口',
    party_panel_description: '選擇興趣湯技，或直接開房找夥伴。',
    party_panel_create_heading: '建立房間',
    party_panel_create_description: '按下按鈕填寫表單，Bot 會建立語音房並通知同好。',
    party_panel_list_heading: '查看房間',
    party_panel_list_description: '挑選進行中的揪團，加入語音後按「進入揪團」。',
    party_panel_create_label: '建立房間',
    party_panel_list_label: '查看房間',
    skill_panel_title: '🏷️ 湯技面板',
    skill_panel_description: '加入湯技即可取得身分組與專屬頻道，可同時加入多個。',
    skill_panel_footer: '邀請碼請向管理員索取',
    leveling_enabled: true,
    xp_per_message_min: 15,
    xp_per_message_max: 25,
    xp_message_cooldown: 60,
    xp_per_voice_tick: 10,
    xp_voice_interval: 300,
    xp_daily_base: 50,
    levelup_channel: '等級公告',
    level_roles: [
      [1, '🌱 湯友 LV1 新手湯友', 0x95a5a6],
      [5, '🍵 湯友 LV5 泡湯常客', 0x3498db],
      [10, '♨️ 湯友 LV10 溫泉達人', 0x2ecc71],
      [20, '💎 湯友 LV20 湯中豪傑', 0x9b59b6],
      [50, '🏆 湯友 LV50 湯神', 0xffd700],
    ],
  }
}

const store = new Map<string, GuildSettings>()
const skillsStore = new Map<string, GuildSkill[]>()

function randomInviteCode(): string {
  const alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
  return Array.from({ length: 8 }, () => alphabet[Math.floor(Math.random() * alphabet.length)]).join('')
}

function defaultSkills(): GuildSkill[] {
  return [
    {
      name: '遊戲術',
      emoji: '🎮',
      category_name: '湯技：遊戲術 🎮',
      role_name: '湯技：遊戲術',
      member_count: 28,
      invite_code: 'GAME7X9K',
      direct_join: true,
    },
    {
      name: '鍛造術',
      emoji: '⚒️',
      category_name: '湯技：鍛造術 ⚒️',
      role_name: '湯技：鍛造術',
      member_count: 14,
      invite_code: 'FORG3M2P',
      direct_join: true,
    },
    {
      name: '墨繪術',
      emoji: '🎨',
      category_name: '湯技：墨繪術 🎨',
      role_name: '湯技：墨繪術',
      member_count: 9,
      invite_code: 'ARTS8Q4W',
      direct_join: true,
    },
    {
      name: '秘傳煉金',
      emoji: '🧪',
      category_name: '湯技：秘傳煉金 🧪',
      role_name: '湯技：秘傳煉金',
      member_count: 5,
      invite_code: 'ALCH5V9Z',
      direct_join: false,
    },
  ]
}

function getMockSettings(guildId: string): GuildSettings {
  if (!store.has(guildId)) store.set(guildId, defaultSettings())
  return store.get(guildId)!
}

function getMockSkills(guildId: string): GuildSkill[] {
  if (!skillsStore.has(guildId)) skillsStore.set(guildId, defaultSkills())
  const currentSettings = getMockSettings(guildId)
  const directSet = new Set(currentSettings.skill_panel_direct_join_skills)
  return skillsStore.get(guildId)!.map((skill) => ({
    ...skill,
    direct_join: directSet.has(skill.name),
  }))
}

function delay<T>(value: T): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), 150))
}

export async function mockRequest(path: string, init?: RequestInit): Promise<unknown> {
  const method = (init?.method ?? 'GET').toUpperCase()
  if (path === '/api/me') return delay({ user })
  if (path === '/api/guilds') return delay({ guilds })

  const match = /^\/api\/guilds\/([^/]+)\/(settings|categories|channels|skills)$/.exec(path)
  if (match) {
    const guildId = decodeURIComponent(match[1]!)
    if (match[2] === 'categories') return delay({ categories })
    if (match[2] === 'channels') return delay({ channels })
    if (match[2] === 'skills') {
      const currentSkills = getMockSkills(guildId)
      if (method === 'GET') {
        return delay({ skills: currentSkills })
      }
      if (method === 'POST') {
        const body = JSON.parse(String(init?.body ?? '{}')) as { name?: string; emoji?: string }
        const name = (body.name ?? '').trim()
        const emoji = body.emoji?.trim() || null
        if (!name) throw new ApiError('請輸入湯技名稱', 422)
        if (name.includes(' ')) throw new ApiError('湯技名稱不可包含空白字元', 422)
        if (currentSkills.some((s) => s.name === name)) {
          throw new ApiError(`湯技「${name}」已經存在`, 409)
        }
        const settings = getMockSettings(guildId)
        const created: GuildSkill = {
          name,
          emoji,
          category_name: emoji ? `${settings.skill_prefix}${name} ${emoji}` : `${settings.skill_prefix}${name}`,
          role_name: `${settings.skill_prefix}${name}`,
          member_count: 1,
          invite_code: randomInviteCode(),
          direct_join: settings.skill_panel_direct_join_skills.includes(name),
        }
        skillsStore.set(guildId, [...currentSkills, created])
        return delay({ skill: created })
      }
    }
    if (method === 'PUT') {
      const body = JSON.parse(String(init?.body ?? '{}')) as GuildSettings
      store.set(guildId, body)
      return delay({ settings: body })
    }
    return delay({ settings: getMockSettings(guildId) })
  }

  const skillActionMatch = /^\/api\/guilds\/([^/]+)\/skills\/([^/]+)(?:\/(regenerate-code))?$/.exec(path)
  if (skillActionMatch) {
    const guildId = decodeURIComponent(skillActionMatch[1]!)
    const skillName = decodeURIComponent(skillActionMatch[2]!)
    const action = skillActionMatch[3]
    const currentSkills = getMockSkills(guildId)

    if (action === 'regenerate-code' && method === 'POST') {
      const target = currentSkills.find((s) => s.name === skillName)
      if (!target) throw new ApiError(`找不到湯技「${skillName}」`, 404)
      const invite_code = randomInviteCode()
      skillsStore.set(
        guildId,
        currentSkills.map((s) => (s.name === skillName ? { ...s, invite_code } : s)),
      )
      return delay({ invite_code })
    }

    if (!action && method === 'DELETE') {
      skillsStore.set(
        guildId,
        currentSkills.filter((s) => s.name !== skillName),
      )
      return delay(null)
    }
  }

  throw new Error(`[mock] Unhandled request: ${method} ${path}`)
}
