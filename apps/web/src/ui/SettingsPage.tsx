import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useParams } from '@tanstack/react-router'
import { ArrowLeft, Check, Save, Settings2 } from 'lucide-react'
import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { useTranslation } from 'react-i18next'
import { getGuildCategories, getGuildSettings, getGuilds, updateGuildSettings } from '../api'
import {
  formToSettings,
  createSettingsFormSchema,
  settingsToForm,
  type SettingsFormValues,
  type ValidSettingsFormValues,
} from '../settings-form'
import { ErrorState, LoadingState } from './States'

type FieldProps = {
  label: string
  hint?: string
  error?: string
  children: React.ReactNode
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

function SettingsForm({ guildId }: { guildId: string }) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const settings = useQuery({
    queryKey: ['guild-settings', guildId],
    queryFn: () => getGuildSettings(guildId),
  })
  const categories = useQuery({
    queryKey: ['guild-categories', guildId],
    queryFn: () => getGuildCategories(guildId),
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

  if (settings.isLoading) return <LoadingState label={t('settings.loading')} />
  if (settings.isError) return <ErrorState message={settings.error.message} onRetry={() => void settings.refetch()} />

  const errors = form.formState.errors
  const inputError = (name: keyof SettingsFormValues) => errors[name]?.message?.toString()
  const selectedPartyCategory = form.watch('party_category')
  const selectedCategoryExists = categories.data?.some((category) => category.name === selectedPartyCategory)

  return (
    <form className="settings-form" onSubmit={form.handleSubmit((values) => mutation.mutate(values))}>
      <section className="settings-section" aria-labelledby="auto-voice-title">
        <div className="section-heading">
          <h2 id="auto-voice-title">{t('settings.sections.autoVoice.title')}</h2>
          <p>{t('settings.sections.autoVoice.description')}</p>
        </div>
        <div className="form-grid">
          <Field label={t('settings.fields.triggerChannel')} error={inputError('auto_voice_trigger')}><input {...form.register('auto_voice_trigger')} /></Field>
          <Field label={t('settings.fields.roomSuffix')} error={inputError('auto_voice_suffix')}><input {...form.register('auto_voice_suffix')} /></Field>
          <Field label={t('settings.fields.defaultUserLimit')} hint={t('settings.hints.userLimit')} error={inputError('auto_voice_limit')}><input type="number" min="0" max="99" {...form.register('auto_voice_limit')} /></Field>
        </div>
      </section>

      <section className="settings-section" aria-labelledby="private-title">
        <div className="section-heading"><h2 id="private-title">{t('settings.sections.privateRooms.title')}</h2><p>{t('settings.sections.privateRooms.description')}</p></div>
        <div className="form-grid">
          <Field label={t('settings.fields.category')} error={inputError('private_category')}><input {...form.register('private_category')} /></Field>
          <Field label={t('settings.fields.triggerChannel')} error={inputError('private_trigger')}><input {...form.register('private_trigger')} /></Field>
          <Field label={t('settings.fields.roomSuffix')} error={inputError('private_suffix')}><input {...form.register('private_suffix')} /></Field>
          <Field label={t('settings.fields.defaultUserLimit')} error={inputError('private_limit')}><input type="number" min="0" max="99" {...form.register('private_limit')} /></Field>
          <Field label={t('settings.fields.passwordChannel')} error={inputError('password_channel')}><input {...form.register('password_channel')} /></Field>
        </div>
      </section>

      <section className="settings-section" aria-labelledby="skills-title">
        <div className="section-heading"><h2 id="skills-title">{t('settings.sections.skills.title')}</h2><p>{t('settings.sections.skills.description')}</p></div>
        <div className="form-grid">
          <Field label={t('settings.fields.commandPrefix')} error={inputError('skill_prefix')}><input {...form.register('skill_prefix')} /></Field>
          <Field label={t('settings.fields.panelChannel')} error={inputError('skill_panel_channel')}><input {...form.register('skill_panel_channel')} /></Field>
          <Field label={t('settings.fields.directJoinSkills')} hint={t('settings.hints.directJoinSkills')} error={inputError('skill_panel_direct_join_skills')}><textarea rows={5} {...form.register('skill_panel_direct_join_skills')} /></Field>
          <Field label={t('settings.fields.partyCategory')} hint={t('settings.hints.partyCategory')} error={inputError('party_category')}>
            <select {...form.register('party_category')} disabled={categories.isLoading}>
              {categories.isLoading && <option value={selectedPartyCategory}>{t('settings.status.loadingCategories')}</option>}
              {!categories.isLoading && selectedPartyCategory && !selectedCategoryExists && <option value={selectedPartyCategory}>{t('settings.status.missingCategory', { category: selectedPartyCategory })}</option>}
              {categories.data?.map((category) => <option key={category.id} value={category.name}>{category.name}</option>)}
            </select>
            {categories.isError && <span className="field-error" role="alert">{categories.error.message}</span>}
          </Field>
        </div>
      </section>

      <section className="settings-section" aria-labelledby="leveling-title">
        <div className="section-heading"><h2 id="leveling-title">{t('settings.sections.leveling.title')}</h2><p>{t('settings.sections.leveling.description')}</p></div>
        <div className="form-grid compact-grid">
          <Field label={t('settings.fields.messageXpMin')} error={inputError('xp_per_message_min')}><input type="number" min="0" {...form.register('xp_per_message_min')} /></Field>
          <Field label={t('settings.fields.messageXpMax')} error={inputError('xp_per_message_max')}><input type="number" min="0" {...form.register('xp_per_message_max')} /></Field>
          <Field label={t('settings.fields.messageCooldown')} error={inputError('xp_message_cooldown')}><input type="number" min="0" {...form.register('xp_message_cooldown')} /></Field>
          <Field label={t('settings.fields.voiceXp')} error={inputError('xp_per_voice_tick')}><input type="number" min="0" {...form.register('xp_per_voice_tick')} /></Field>
          <Field label={t('settings.fields.voiceInterval')} error={inputError('xp_voice_interval')}><input type="number" min="1" {...form.register('xp_voice_interval')} /></Field>
          <Field label={t('settings.fields.dailyXp')} error={inputError('xp_daily_base')}><input type="number" min="0" {...form.register('xp_daily_base')} /></Field>
          <Field label={t('settings.fields.levelUpChannel')} error={inputError('levelup_channel')}><input {...form.register('levelup_channel')} /></Field>
          <Field label={t('settings.fields.levelRoles')} hint={t('settings.hints.levelRoles')} error={inputError('level_roles')}><textarea className="code-input" rows={8} spellCheck="false" {...form.register('level_roles')} /></Field>
        </div>
      </section>

      <div className="save-bar">
        <div className="save-status" aria-live="polite">
          {mutation.isError && <span className="save-error">{mutation.error.message}</span>}
          {mutation.isSuccess && !form.formState.isDirty && <span className="save-success"><Check aria-hidden="true" /> {t('settings.status.saved')}</span>}
          {form.formState.isDirty && <span>{t('settings.status.unsaved')}</span>}
        </div>
        <button className="button primary" type="submit" disabled={mutation.isPending || !form.formState.isDirty}>
          <Save aria-hidden="true" /> {mutation.isPending ? t('settings.status.saving') : t('settings.status.save')}
        </button>
      </div>
    </form>
  )
}

export function SettingsPage() {
  const { t } = useTranslation()
  const { guildId } = useParams({ from: '/authenticated/guilds/$guildId/settings' })
  const guilds = useQuery({ queryKey: ['guilds'], queryFn: getGuilds })
  const guild = guilds.data?.find((item) => item.id === guildId)

  return (
    <main className="page">
      <Link className="back-link" to="/guilds"><ArrowLeft aria-hidden="true" /> {t('settings.allServers')}</Link>
      <div className="page-heading settings-heading">
        <div><p className="eyebrow">{t('settings.eyebrow')}</p><h1>{guild?.name ?? t('settings.fallbackServer')}</h1><p>{t('settings.description')}</p></div>
        <div className="heading-icon"><Settings2 aria-hidden="true" /></div>
      </div>
      <SettingsForm guildId={guildId} />
    </main>
  )
}