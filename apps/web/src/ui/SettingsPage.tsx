import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useParams } from '@tanstack/react-router'
import {
  ArrowLeft,
  ArrowRight,
  Check,
  ChevronRight,
  LayoutGrid,
  Loader2,
  Megaphone,
  Mic,
  Save,
  Sparkles,
  SquareTerminal,
  Trophy,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { useTranslation } from 'react-i18next'
import { getGuildChannels, getGuildSettings, getGuilds, updateGuildSettings } from '../api'
import {
  formToSettings,
  createSettingsFormSchema,
  settingsToForm,
  type SettingsFormValues,
  type ValidSettingsFormValues,
} from '../settings-form'
import { ErrorState, LoadingState } from './States'
import { LevelRolesEditor } from './LevelRolesEditor'
import { SkillsManager } from './SkillsManager'

type ModuleView = 'dashboard' | 'voice' | 'skills' | 'roomPanel' | 'leveling' | 'slash'

const MODULE_FIELDS: Record<'voice' | 'skills' | 'roomPanel' | 'leveling', (keyof SettingsFormValues)[]> = {
  voice: [
    'auto_voice_enabled',
    'auto_voice_trigger',
    'auto_voice_suffix',
    'auto_voice_limit',
    'private_rooms_enabled',
    'private_category',
    'private_trigger',
    'private_suffix',
    'private_limit',
    'password_channel',
  ],
  skills: [
    'skills_enabled',
    'skill_prefix',
    'skill_panel_channel',
    'skill_panel_direct_join_skills',
    'skill_panel_title',
    'skill_panel_description',
    'skill_panel_footer',
  ],
  roomPanel: [
    'party_enabled',
    'party_notification_channel',
    'party_panel_title',
    'party_panel_description',
    'party_panel_create_heading',
    'party_panel_create_description',
    'party_panel_list_heading',
    'party_panel_list_description',
    'party_panel_create_label',
    'party_panel_list_label',
  ],
  leveling: [
    'leveling_enabled',
    'xp_per_message_min',
    'xp_per_message_max',
    'xp_message_cooldown',
    'xp_per_voice_tick',
    'xp_voice_interval',
    'xp_daily_base',
    'levelup_channel',
    'level_roles',
  ],
}

const slashCommandGroups = [
  { key: 'general', commands: ['/help [category]', '/userinfo [user]', '/announce <title> <content>'] },
  { key: 'voice', commands: ['/voice-name <name>', '/voice-limit <limit>', '/voice-kick <user>', '/setup-voice', '/voice-invite <user>', '/setup-private', '/fix-private-perms'] },
  { key: 'party', commands: ['/party setup', '/party create', '/party list'] },
  { key: 'skills', commands: ['/skill create <name> [emoji]', '/skill delete <name>', '/skill join <invite-code>', '/skill leave <name>', '/skill info <name> [regenerate]', '/skill regen <name>', '/skill list', '/skill setup', '/skill panel'] },
  { key: 'leveling', commands: ['/daily', '/rank [user]', '/leaderboard', '/level-preview', '/level-init'] },
] as const

const totalSlashCommands = slashCommandGroups.reduce((sum, group) => sum + group.commands.length, 0)

const commandKey = (command: string) => {
  const [root, subcommand] = command.replace(/^\//, '').split(' ')
  const key = subcommand && !subcommand.startsWith('<') && !subcommand.startsWith('[')
    ? `${root}_${subcommand}`
    : root
  return key!.replaceAll('-', '_')
}

type FieldProps = {
  label: string
  hint?: string
  error?: string
  children: React.ReactNode
}

function ToggleSwitch({
  label,
  checked,
  onChange,
  disabled,
}: {
  label: string
  checked: boolean
  onChange: (checked: boolean) => void
  disabled?: boolean
}) {
  return (
    <label className={`toggle-switch-control ${checked ? 'is-enabled' : 'is-disabled'}`}>
      <span className="toggle-switch-track">
        <input
          type="checkbox"
          checked={checked}
          onChange={(e) => onChange(e.target.checked)}
          disabled={disabled}
        />
        <span className="toggle-switch-thumb" />
      </span>
      <span className="toggle-switch-text">{label}</span>
    </label>
  )
}

function Field({ label, hint, error, children }: FieldProps) {
  return (
    <label className="field">
      <span className="field-label">{label}</span>
      {hint && <span className="field-hint">{hint}</span>}
      {children}
      {error && <span className="field-error" role="alert">{error}</span>}
    </label>
  )
}

function SlashCommandGuide() {
  const { t } = useTranslation()

  return (
    <div className="command-guide">
      <div className="command-intro">
        <SquareTerminal aria-hidden="true" />
        <div>
          <h2>{t('settings.slash.title')}</h2>
          <p>{t('settings.slash.description')}</p>
        </div>
      </div>
      {slashCommandGroups.map((group) => (
        <section className="command-group" key={group.key} aria-labelledby={`command-group-${group.key}`}>
          <div className="command-group-heading">
            <h3 id={`command-group-${group.key}`}>{t(`settings.slash.groups.${group.key}`)}</h3>
            <span>{t('settings.slash.commandCount', { count: group.commands.length })}</span>
          </div>
          <div className="command-list">
            {group.commands.map((command) => (
              <div className="command-row" key={command}>
                <code>{command}</code>
                <p>{t(`settings.slash.commands.${commandKey(command)}`)}</p>
              </div>
            ))}
          </div>
        </section>
      ))}
    </div>
  )
}

export function SettingsPage() {
  const { t } = useTranslation()
  const [activeView, setActiveView] = useState<ModuleView>('dashboard')
  const [justSaved, setJustSaved] = useState(false)
  const { guildId } = useParams({ from: '/authenticated/guilds/$guildId/settings' })
  const queryClient = useQueryClient()

  const guilds = useQuery({ queryKey: ['guilds'], queryFn: getGuilds })
  const guild = guilds.data?.find((item) => item.id === guildId)

  const settings = useQuery({
    queryKey: ['guild-settings', guildId],
    queryFn: () => getGuildSettings(guildId),
  })
  const channels = useQuery({
    queryKey: ['guild-channels', guildId],
    queryFn: () => getGuildChannels(guildId),
  })

  const form = useForm<SettingsFormValues, unknown, ValidSettingsFormValues>({
    resolver: zodResolver(createSettingsFormSchema(t)),
  })

  const mutation = useMutation({
    mutationFn: (values: ValidSettingsFormValues) =>
      updateGuildSettings(guildId, formToSettings(values)),
    onSuccess: (saved) => {
      queryClient.setQueryData(['guild-settings', guildId], saved)
      form.reset(settingsToForm(saved))
      setJustSaved(true)
      window.setTimeout(() => setJustSaved(false), 2000)
    },
  })

  useEffect(() => {
    if (settings.data) form.reset(settingsToForm(settings.data))
  }, [form, settings.data])

  useEffect(() => {
    const warnUnsaved = (event: BeforeUnloadEvent) => {
      if (form.formState.isDirty) event.preventDefault()
    }
    window.addEventListener('beforeunload', warnUnsaved)
    return () => window.removeEventListener('beforeunload', warnUnsaved)
  }, [form.formState.isDirty])

  const errors = form.formState.errors
  const dirtyFields = form.formState.dirtyFields
  const inputError = (name: keyof SettingsFormValues) => errors[name]?.message?.toString()

  const isModuleDirty = (mod: keyof typeof MODULE_FIELDS) =>
    MODULE_FIELDS[mod].some((field) => Boolean(dirtyFields[field]))
  const isModuleError = (mod: keyof typeof MODULE_FIELDS) =>
    MODULE_FIELDS[mod].some((field) => Boolean(errors[field]))

  const values = form.watch()
  const selectedNotificationChannel = values.party_notification_channel
  const matchedNotificationChannel = channels.data?.find(
    (ch) => ch.id === selectedNotificationChannel || ch.name === selectedNotificationChannel,
  )

  const directSkillsCount = (values.skill_panel_direct_join_skills ?? '')
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean).length

  const levelRolesCount = (() => {
    try {
      const parsed = JSON.parse(values.level_roles ?? '[]') as unknown
      return Array.isArray(parsed) ? parsed.length : 0
    } catch {
      return 0
    }
  })()

  const moduleCards: {
    id: keyof typeof MODULE_FIELDS
    icon: React.ReactNode
    title: string
    description: string
    isEnabled: boolean
    pills: string[]
  }[] = [
    {
      id: 'voice',
      icon: <Mic aria-hidden="true" />,
      title: t('settings.tabs.voice'),
      description: t('settings.sections.autoVoice.description'),
      isEnabled: (values.auto_voice_enabled ?? true) || (values.private_rooms_enabled ?? true),
      pills: [
        values.auto_voice_trigger || '—',
        values.private_category || '—',
        values.password_channel || '—',
      ],
    },
    {
      id: 'skills',
      icon: <Sparkles aria-hidden="true" />,
      title: t('settings.tabs.skills'),
      description: t('settings.sections.skills.description'),
      isEnabled: values.skills_enabled ?? true,
      pills: [
        values.skill_panel_channel || '—',
        t('settings.dashboard.activeSkillsCount', { count: directSkillsCount }),
        values.skill_prefix || '—',
      ],
    },
    {
      id: 'roomPanel',
      icon: <Megaphone aria-hidden="true" />,
      title: t('settings.tabs.roomPanel'),
      description: t('settings.sections.roomPanel.description'),
      isEnabled: values.party_enabled ?? true,
      pills: [
        matchedNotificationChannel
          ? `#${matchedNotificationChannel.name}`
          : values.party_notification_channel || '—',
        values.party_panel_title || '—',
        values.party_panel_create_label || '—',
      ],
    },
    {
      id: 'leveling',
      icon: <Trophy aria-hidden="true" />,
      title: t('settings.tabs.leveling'),
      description: t('settings.sections.leveling.description'),
      isEnabled: values.leveling_enabled ?? true,
      pills: [
        t('settings.dashboard.xpRange', {
          min: values.xp_per_message_min ?? 15,
          max: values.xp_per_message_max ?? 25,
        }),
        `#${values.levelup_channel || '—'}`,
        t('settings.dashboard.levelRolesCount', { count: levelRolesCount }),
      ],
    },
  ]

  const handleToggleModule = (id: keyof typeof MODULE_FIELDS, checked: boolean) => {
    if (id === 'voice') {
      form.setValue('auto_voice_enabled', checked, { shouldDirty: true, shouldTouch: true, shouldValidate: true })
      form.setValue('private_rooms_enabled', checked, { shouldDirty: true, shouldTouch: true, shouldValidate: true })
    } else if (id === 'skills') {
      form.setValue('skills_enabled', checked, { shouldDirty: true, shouldTouch: true, shouldValidate: true })
    } else if (id === 'roomPanel') {
      form.setValue('party_enabled', checked, { shouldDirty: true, shouldTouch: true, shouldValidate: true })
    } else if (id === 'leveling') {
      form.setValue('leveling_enabled', checked, { shouldDirty: true, shouldTouch: true, shouldValidate: true })
    }
  }

  useEffect(() => {
    if (activeView !== 'dashboard' && activeView !== 'slash') {
      const currentCard = moduleCards.find((c) => c.id === activeView)
      if (currentCard && !currentCard.isEnabled) {
        setActiveView('dashboard')
      }
    }
  }, [activeView, moduleCards])

  const isFormModuleView = activeView !== 'dashboard' && activeView !== 'slash'
  const triggerSave = form.handleSubmit((submitted) => mutation.mutate(submitted))

  return (
    <main className="page">
      <Link className="back-link" to="/guilds">
        <ArrowLeft aria-hidden="true" /> {t('settings.allServers')}
      </Link>
      <div className="page-heading settings-heading">
        <div>
          <p className="eyebrow">{t('settings.eyebrow')}</p>
          <h1>{guild?.name ?? t('settings.fallbackServer')}</h1>
          <p>{t('settings.description')}</p>
        </div>
        <div className="heading-actions">
          {mutation.isError && (
            <span className="save-error" role="alert">
              {mutation.error.message}
            </span>
          )}
          {justSaved && !form.formState.isDirty && (
            <span className="save-success" role="status">
              {t('settings.status.saved')}
            </span>
          )}
          <button
            type="button"
            className={`heading-icon save-icon-button ${form.formState.isDirty ? 'is-dirty' : ''} ${
              justSaved && !form.formState.isDirty ? 'is-saved' : ''
            }`}
            aria-label={t('settings.status.save')}
            title={
              mutation.isPending
                ? t('settings.status.saving')
                : form.formState.isDirty
                  ? `${t('settings.status.save')} (${t('settings.status.unsaved')})`
                  : t('settings.status.save')
            }
            disabled={mutation.isPending}
            onClick={() => void triggerSave()}
          >
            {mutation.isPending ? (
              <Loader2 className="spin" aria-hidden="true" />
            ) : justSaved && !form.formState.isDirty ? (
              <Check aria-hidden="true" />
            ) : (
              <Save aria-hidden="true" />
            )}
          </button>
        </div>
      </div>

      {settings.isLoading && <LoadingState label={t('settings.loading')} />}
      {settings.isError && (
        <ErrorState message={settings.error.message} onRetry={() => void settings.refetch()} />
      )}

      {settings.data && (
        <div className="workspace-layout">
          {/* 方案 A：左側垂直模組導覽列 */}
          <aside className="module-sidebar" aria-label={t('settings.tabs.label')}>
            <div className="sidebar-group">
              <button
                type="button"
                className="sidebar-item"
                aria-current={activeView === 'dashboard' ? 'page' : undefined}
                onClick={() => setActiveView('dashboard')}
              >
                <LayoutGrid aria-hidden="true" />
                <span className="sidebar-item-label">{t('settings.tabs.dashboard')}</span>
              </button>
            </div>

            <div className="sidebar-group">
              <p className="sidebar-group-title">{t('settings.tabs.modulesGroup')}</p>
              {moduleCards
                .filter((mod) => mod.isEnabled)
                .map((mod) => {
                  const dirty = isModuleDirty(mod.id)
                  const hasError = isModuleError(mod.id)
                  return (
                    <button
                      key={mod.id}
                      type="button"
                      className="sidebar-item"
                      aria-current={activeView === mod.id ? 'page' : undefined}
                      onClick={() => setActiveView(mod.id)}
                    >
                      {mod.icon}
                      <span className="sidebar-item-label">{mod.title}</span>
                      {hasError ? (
                        <span className="status-dot error-dot" title="Error" />
                      ) : dirty ? (
                        <span className="status-dot dirty-dot" title={t('settings.dashboard.unsavedBadge')} />
                      ) : null}
                    </button>
                  )
                })}
              {moduleCards.filter((mod) => mod.isEnabled).length === 0 && (
                <span className="sidebar-empty-hint">{t('settings.dashboard.noActiveModules')}</span>
              )}
            </div>

            <div className="sidebar-group">
              <p className="sidebar-group-title">{t('settings.tabs.referenceGroup')}</p>
              <button
                type="button"
                className="sidebar-item"
                aria-current={activeView === 'slash' ? 'page' : undefined}
                onClick={() => setActiveView('slash')}
              >
                <SquareTerminal aria-hidden="true" />
                <span className="sidebar-item-label">{t('settings.tabs.slash')}</span>
              </button>
            </div>
          </aside>

          {/* 右側主工作區：可顯示方案 B 模組卡片牆、單一模組設定表單、或指令手冊 */}
          <div className="module-content">
            {activeView === 'dashboard' && (
              <div className="dashboard-view">
                <div className="dashboard-intro">
                  <h2>{t('settings.dashboard.title')}</h2>
                  <p>{t('settings.dashboard.description')}</p>
                </div>

                <div className="module-grid">
                  {moduleCards.map((mod) => {
                    const dirty = isModuleDirty(mod.id)
                    const hasError = isModuleError(mod.id)
                    return (
                      <article
                        key={mod.id}
                        className={`module-card ${hasError ? 'has-error' : dirty ? 'is-dirty' : ''}`}
                      >
                        <div className="module-card-header">
                          <span className="module-card-icon">{mod.icon}</span>
                          <div className="module-card-titles">
                            <h3>{mod.title}</h3>
                            <div style={{ display: 'inline-flex', gap: '8px', alignItems: 'center' }}>
                              <ToggleSwitch
                                label={mod.isEnabled ? t('common.enabled') : t('common.disabled')}
                                checked={mod.isEnabled}
                                onChange={(checked) => handleToggleModule(mod.id, checked)}
                              />
                              {dirty && !hasError && (
                                <span className="module-badge dirty">{t('settings.dashboard.unsavedBadge')}</span>
                              )}
                            </div>
                          </div>
                        </div>
                        <p className="module-card-desc">{mod.description}</p>
                        <div className="module-card-pills">
                          {mod.pills.map((pill, idx) => (
                            <span key={idx} className="module-pill">
                              {pill}
                            </span>
                          ))}
                        </div>
                        <button
                          type="button"
                          className="module-card-action"
                          onClick={() => setActiveView(mod.id)}
                        >
                          <span>{t('settings.dashboard.configureModule')}</span>
                          <ArrowRight aria-hidden="true" />
                        </button>
                      </article>
                    )
                  })}
                </div>

                <div className="module-banner-card">
                  <div className="module-banner-info">
                    <span className="module-card-icon">
                      <SquareTerminal aria-hidden="true" />
                    </span>
                    <div>
                      <h3>{t('settings.slash.title')}</h3>
                      <p>{t('settings.slash.description')}</p>
                    </div>
                  </div>
                  <button
                    type="button"
                    className="button secondary"
                    onClick={() => setActiveView('slash')}
                  >
                    <span>
                      {t('settings.dashboard.viewGuide')} ({t('settings.slash.commandCount', { count: totalSlashCommands })})
                    </span>
                    <ChevronRight aria-hidden="true" />
                  </button>
                </div>
              </div>
            )}

            {activeView === 'slash' && <SlashCommandGuide />}

            <form
              className="settings-form"
              hidden={!isFormModuleView}
              onSubmit={triggerSave}
            >
              <div hidden={activeView !== 'voice'} className="module-sections">
                <section className="settings-section" aria-labelledby="auto-voice-title">
                  <div className="section-heading has-switch">
                    <div>
                      <h2 id="auto-voice-title">{t('settings.sections.autoVoice.title')}</h2>
                      <p>{t('settings.sections.autoVoice.description')}</p>
                    </div>
                    <ToggleSwitch
                      label={values.auto_voice_enabled ? t('common.enabled') : t('common.disabled')}
                      checked={values.auto_voice_enabled ?? true}
                      onChange={(checked) =>
                        form.setValue('auto_voice_enabled', checked, {
                          shouldDirty: true,
                          shouldTouch: true,
                          shouldValidate: true,
                        })
                      }
                    />
                  </div>
                  {!values.auto_voice_enabled && (
                    <div className="module-disabled-banner">{t('common.disabledNotice')}</div>
                  )}
                  <div className="form-grid">
                    <Field label={t('settings.fields.triggerChannel')} error={inputError('auto_voice_trigger')}>
                      <input {...form.register('auto_voice_trigger')} disabled={!values.auto_voice_enabled} />
                    </Field>
                    <Field label={t('settings.fields.roomSuffix')} error={inputError('auto_voice_suffix')}>
                      <input {...form.register('auto_voice_suffix')} disabled={!values.auto_voice_enabled} />
                    </Field>
                    <Field
                      label={t('settings.fields.defaultUserLimit')}
                      hint={t('settings.hints.userLimit')}
                      error={inputError('auto_voice_limit')}
                    >
                      <input type="number" min="0" max="99" {...form.register('auto_voice_limit')} disabled={!values.auto_voice_enabled} />
                    </Field>
                  </div>
                </section>

                <section className="settings-section" aria-labelledby="private-title">
                  <div className="section-heading has-switch">
                    <div>
                      <h2 id="private-title">{t('settings.sections.privateRooms.title')}</h2>
                      <p>{t('settings.sections.privateRooms.description')}</p>
                    </div>
                    <ToggleSwitch
                      label={values.private_rooms_enabled ? t('common.enabled') : t('common.disabled')}
                      checked={values.private_rooms_enabled ?? true}
                      onChange={(checked) =>
                        form.setValue('private_rooms_enabled', checked, {
                          shouldDirty: true,
                          shouldTouch: true,
                          shouldValidate: true,
                        })
                      }
                    />
                  </div>
                  {!values.private_rooms_enabled && (
                    <div className="module-disabled-banner">{t('common.disabledNotice')}</div>
                  )}
                  <div className="form-grid">
                    <Field label={t('settings.fields.category')} error={inputError('private_category')}>
                      <input {...form.register('private_category')} disabled={!values.private_rooms_enabled} />
                    </Field>
                    <Field label={t('settings.fields.triggerChannel')} error={inputError('private_trigger')}>
                      <input {...form.register('private_trigger')} disabled={!values.private_rooms_enabled} />
                    </Field>
                    <Field label={t('settings.fields.roomSuffix')} error={inputError('private_suffix')}>
                      <input {...form.register('private_suffix')} disabled={!values.private_rooms_enabled} />
                    </Field>
                    <Field label={t('settings.fields.defaultUserLimit')} error={inputError('private_limit')}>
                      <input type="number" min="0" max="99" {...form.register('private_limit')} disabled={!values.private_rooms_enabled} />
                    </Field>
                    <Field label={t('settings.fields.passwordChannel')} error={inputError('password_channel')}>
                      <input {...form.register('password_channel')} disabled={!values.private_rooms_enabled} />
                    </Field>
                  </div>
                </section>
              </div>

              <div hidden={activeView !== 'skills'} className="module-sections">
                <section className="settings-section" aria-label="湯技建立與清單管理">
                  <SkillsManager
                    guildId={guildId}
                    skillPrefix={values.skill_prefix ?? '湯技：'}
                    directJoinText={values.skill_panel_direct_join_skills ?? ''}
                    onChangeDirectJoinText={(next) =>
                      form.setValue('skill_panel_direct_join_skills', next, {
                        shouldDirty: true,
                        shouldTouch: true,
                        shouldValidate: true,
                      })
                    }
                  />
                </section>

                <section className="settings-section" aria-labelledby="skills-title">
                  <div className="section-heading has-switch">
                    <div>
                      <h2 id="skills-title">{t('settings.sections.skills.title')}</h2>
                      <p>{t('settings.sections.skills.description')}</p>
                    </div>
                    <ToggleSwitch
                      label={values.skills_enabled ? t('common.enabled') : t('common.disabled')}
                      checked={values.skills_enabled ?? true}
                      onChange={(checked) =>
                        form.setValue('skills_enabled', checked, {
                          shouldDirty: true,
                          shouldTouch: true,
                          shouldValidate: true,
                        })
                      }
                    />
                  </div>
                  {!values.skills_enabled && (
                    <div className="module-disabled-banner">{t('common.disabledNotice')}</div>
                  )}
                  <div className="form-grid">
                    <Field label={t('settings.fields.commandPrefix')} error={inputError('skill_prefix')}>
                      <input {...form.register('skill_prefix')} />
                    </Field>
                    <Field label={t('settings.fields.panelChannel')} error={inputError('skill_panel_channel')}>
                      <input {...form.register('skill_panel_channel')} />
                    </Field>
                    <Field
                      label={t('settings.fields.directJoinSkills')}
                      hint={t('settings.hints.directJoinSkills')}
                      error={inputError('skill_panel_direct_join_skills')}
                    >
                      <textarea rows={5} {...form.register('skill_panel_direct_join_skills')} />
                    </Field>
                    <Field label={t('settings.fields.panelTitle')} error={inputError('skill_panel_title')}>
                      <input maxLength={256} {...form.register('skill_panel_title')} />
                    </Field>
                    <Field
                      label={t('settings.fields.panelDescription')}
                      hint={t('settings.hints.skillPanelDescription')}
                      error={inputError('skill_panel_description')}
                    >
                      <textarea rows={8} maxLength={4096} {...form.register('skill_panel_description')} />
                    </Field>
                    <Field
                      label={t('settings.fields.panelFooter')}
                      hint={t('settings.hints.panelFooter')}
                      error={inputError('skill_panel_footer')}
                    >
                      <textarea rows={3} maxLength={2048} {...form.register('skill_panel_footer')} />
                    </Field>
                  </div>
                </section>
              </div>

              <div hidden={activeView !== 'roomPanel'} className="module-sections">
                <section className="settings-section" aria-labelledby="room-panel-title">
                  <div className="section-heading has-switch">
                    <div>
                      <h2 id="room-panel-title">{t('settings.sections.roomPanel.title')}</h2>
                      <p>{t('settings.sections.roomPanel.description')}</p>
                    </div>
                    <ToggleSwitch
                      label={values.party_enabled ? t('common.enabled') : t('common.disabled')}
                      checked={values.party_enabled ?? true}
                      onChange={(checked) =>
                        form.setValue('party_enabled', checked, {
                          shouldDirty: true,
                          shouldTouch: true,
                          shouldValidate: true,
                        })
                      }
                    />
                  </div>
                  {!values.party_enabled && (
                    <div className="module-disabled-banner">{t('common.disabledNotice')}</div>
                  )}
                  <div className="form-grid">
                    <Field
                      label={t('settings.fields.partyNotificationChannel')}
                      hint={t('settings.hints.partyNotificationChannel')}
                      error={inputError('party_notification_channel')}
                    >
                      <select {...form.register('party_notification_channel')} disabled={channels.isLoading}>
                        {channels.isLoading && (
                          <option value={selectedNotificationChannel}>
                            {t('settings.status.loadingCategories')}
                          </option>
                        )}
                        {!channels.isLoading && selectedNotificationChannel && !matchedNotificationChannel && (
                          <option value={selectedNotificationChannel}>
                            {selectedNotificationChannel}
                          </option>
                        )}
                        {channels.data?.map((channel) => {
                          const optionValue =
                            selectedNotificationChannel === channel.name ? channel.name : channel.id
                          const label = channel.category
                            ? `${channel.category} ／ #${channel.name}`
                            : `#${channel.name}`
                          return (
                            <option key={channel.id} value={optionValue}>
                              {label}
                            </option>
                          )
                        })}
                      </select>
                      {channels.isError && (
                        <span className="field-error" role="alert">
                          {channels.error.message}
                        </span>
                      )}
                    </Field>
                    <Field label={t('settings.fields.panelTitle')} error={inputError('party_panel_title')}>
                      <input maxLength={256} {...form.register('party_panel_title')} />
                    </Field>
                    <Field
                      label={t('settings.fields.panelDescription')}
                      hint={t('settings.hints.panelDescription')}
                      error={inputError('party_panel_description')}
                    >
                      <textarea rows={6} maxLength={4096} {...form.register('party_panel_description')} />
                    </Field>
                    <Field label={t('settings.fields.createHeading')} error={inputError('party_panel_create_heading')}>
                      <input maxLength={256} {...form.register('party_panel_create_heading')} />
                    </Field>
                    <Field
                      label={t('settings.fields.createDescription')}
                      error={inputError('party_panel_create_description')}
                    >
                      <textarea rows={3} maxLength={1024} {...form.register('party_panel_create_description')} />
                    </Field>
                    <Field label={t('settings.fields.listHeading')} error={inputError('party_panel_list_heading')}>
                      <input maxLength={256} {...form.register('party_panel_list_heading')} />
                    </Field>
                    <Field label={t('settings.fields.listDescription')} error={inputError('party_panel_list_description')}>
                      <textarea rows={3} maxLength={1024} {...form.register('party_panel_list_description')} />
                    </Field>
                    <Field label={t('settings.fields.createButton')} error={inputError('party_panel_create_label')}>
                      <input maxLength={80} {...form.register('party_panel_create_label')} />
                    </Field>
                    <Field label={t('settings.fields.listButton')} error={inputError('party_panel_list_label')}>
                      <input maxLength={80} {...form.register('party_panel_list_label')} />
                    </Field>
                  </div>
                </section>
              </div>

              <div hidden={activeView !== 'leveling'} className="module-sections">
                <section className="settings-section" aria-labelledby="leveling-title">
                  <div className="section-heading has-switch">
                    <div>
                      <h2 id="leveling-title">{t('settings.sections.leveling.title')}</h2>
                      <p>{t('settings.sections.leveling.description')}</p>
                    </div>
                    <ToggleSwitch
                      label={values.leveling_enabled ? t('common.enabled') : t('common.disabled')}
                      checked={values.leveling_enabled ?? true}
                      onChange={(checked) =>
                        form.setValue('leveling_enabled', checked, {
                          shouldDirty: true,
                          shouldTouch: true,
                          shouldValidate: true,
                        })
                      }
                    />
                  </div>
                  {!values.leveling_enabled && (
                    <div className="module-disabled-banner">{t('common.disabledNotice')}</div>
                  )}
                  <div className="xp-grid">
                    <Field label={t('settings.fields.messageXpMin')} error={inputError('xp_per_message_min')}>
                      <input type="number" min="0" {...form.register('xp_per_message_min')} />
                    </Field>
                    <Field label={t('settings.fields.messageXpMax')} error={inputError('xp_per_message_max')}>
                      <input type="number" min="0" {...form.register('xp_per_message_max')} />
                    </Field>
                    <Field label={t('settings.fields.messageCooldown')} error={inputError('xp_message_cooldown')}>
                      <input type="number" min="0" {...form.register('xp_message_cooldown')} />
                    </Field>
                    <Field label={t('settings.fields.voiceXp')} error={inputError('xp_per_voice_tick')}>
                      <input type="number" min="0" {...form.register('xp_per_voice_tick')} />
                    </Field>
                    <Field label={t('settings.fields.voiceInterval')} error={inputError('xp_voice_interval')}>
                      <input type="number" min="1" {...form.register('xp_voice_interval')} />
                    </Field>
                    <Field label={t('settings.fields.dailyXp')} error={inputError('xp_daily_base')}>
                      <input type="number" min="0" {...form.register('xp_daily_base')} />
                    </Field>
                    <div className="xp-channel-field">
                      <Field label={t('settings.fields.levelUpChannel')} error={inputError('levelup_channel')}>
                        <input {...form.register('levelup_channel')} />
                      </Field>
                    </div>
                  </div>
                </section>

                <section className="settings-section" aria-labelledby="level-roles-title">
                  <div className="section-heading">
                    <h2 id="level-roles-title">{t('settings.fields.levelRoles')}</h2>
                    <p>{t('settings.hints.levelRoles')}</p>
                  </div>
                  <div className="level-roles-block">
                    <LevelRolesEditor
                      value={values.level_roles ?? '[]'}
                      onChange={(next) =>
                        form.setValue('level_roles', next, {
                          shouldDirty: true,
                          shouldTouch: true,
                          shouldValidate: true,
                        })
                      }
                    />
                    {inputError('level_roles') && (
                      <span className="field-error" role="alert">
                        {inputError('level_roles')}
                      </span>
                    )}
                  </div>
                </section>
              </div>
            </form>
          </div>
        </div>
      )}
    </main>
  )
}
