import { z } from 'zod'
import type { GuildSettings } from './api'

const requiredText = z.string().trim().min(1, 'This field is required')

function validateLevelRoles(value: string, context: z.RefinementCtx) {
  const addIssue = (message: string) =>
    context.addIssue({ code: 'custom', path: ['level_roles'], message })

  try {
    const parsed = JSON.parse(value) as unknown
    const result = z
      .array(z.tuple([z.number().int().positive(), requiredText, z.number().int().min(0).max(0xffffff)]))
      .min(1)
      .safeParse(parsed)
    if (!result.success) {
      addIssue('Use [[level, "Role name", colorNumber], ...]')
      return
    }

    const levels = result.data.map(([level]) => level)
    const names = result.data.map(([, name]) => name)
    if (new Set(levels).size !== levels.length || new Set(names).size !== names.length) {
      addIssue('Role levels and names must be unique')
      return
    }
    if (levels.some((level, index) => index > 0 && level < levels[index - 1]!)) {
      addIssue('Roles must be ordered by level')
    }
  } catch {
    addIssue('Enter valid JSON')
  }
}

export const settingsFormSchema = z
  .object({
    auto_voice_trigger: requiredText,
    auto_voice_suffix: requiredText,
    auto_voice_limit: z.coerce.number().int().min(0).max(99),
    private_category: requiredText,
    private_trigger: requiredText,
    private_suffix: requiredText,
    private_limit: z.coerce.number().int().min(0).max(99),
    password_channel: requiredText,
    skill_prefix: requiredText,
    skill_panel_channel: requiredText,
    skill_panel_direct_join_skills: z.string(),
    xp_per_message_min: z.coerce.number().int().min(0),
    xp_per_message_max: z.coerce.number().int().min(0),
    xp_message_cooldown: z.coerce.number().int().min(0),
    xp_per_voice_tick: z.coerce.number().int().min(0),
    xp_voice_interval: z.coerce.number().int().min(1),
    xp_daily_base: z.coerce.number().int().min(0),
    levelup_channel: requiredText,
    level_roles: z.string(),
  })
  .superRefine((values, context) => {
    if (values.auto_voice_trigger.toLocaleLowerCase() === values.private_trigger.toLocaleLowerCase()) {
      context.addIssue({
        code: 'custom',
        path: ['private_trigger'],
        message: 'Trigger names must be different',
      })
    }
    if (values.xp_per_message_min > values.xp_per_message_max) {
      context.addIssue({
        code: 'custom',
        path: ['xp_per_message_max'],
        message: 'Maximum must be at least the minimum',
      })
    }
    const skills = values.skill_panel_direct_join_skills
      .split('\n')
      .map((value) => value.trim())
      .filter(Boolean)
    if (new Set(skills).size !== skills.length) {
      context.addIssue({
        code: 'custom',
        path: ['skill_panel_direct_join_skills'],
        message: 'Skill names must be unique',
      })
    }
    validateLevelRoles(values.level_roles, context)
  })

export type SettingsFormValues = z.input<typeof settingsFormSchema>
export type ValidSettingsFormValues = z.output<typeof settingsFormSchema>

export function settingsToForm(settings: GuildSettings): ValidSettingsFormValues {
  return {
    ...settings,
    skill_panel_direct_join_skills: settings.skill_panel_direct_join_skills.join('\n'),
    level_roles: JSON.stringify(settings.level_roles, null, 2),
  }
}

export function formToSettings(values: ValidSettingsFormValues): GuildSettings {
  return {
    ...values,
    skill_panel_direct_join_skills: values.skill_panel_direct_join_skills
      .split('\n')
      .map((value) => value.trim())
      .filter(Boolean),
    level_roles: JSON.parse(values.level_roles) as GuildSettings['level_roles'],
  }
}