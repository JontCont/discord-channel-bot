import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useParams } from '@tanstack/react-router'
import { ArrowLeft, Check, Save, Settings2 } from 'lucide-react'
import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { getGuildSettings, getGuilds, updateGuildSettings } from '../api'
import {
  formToSettings,
  settingsFormSchema,
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
  const queryClient = useQueryClient()
  const settings = useQuery({
    queryKey: ['guild-settings', guildId],
    queryFn: () => getGuildSettings(guildId),
  })
  const form = useForm<SettingsFormValues, unknown, ValidSettingsFormValues>({
    resolver: zodResolver(settingsFormSchema),
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

  if (settings.isLoading) return <LoadingState label="Loading server settings" />
  if (settings.isError) return <ErrorState message={settings.error.message} onRetry={() => void settings.refetch()} />

  const errors = form.formState.errors
  const inputError = (name: keyof SettingsFormValues) => errors[name]?.message?.toString()

  return (
    <form className="settings-form" onSubmit={form.handleSubmit((values) => mutation.mutate(values))}>
      <section className="settings-section" aria-labelledby="auto-voice-title">
        <div className="section-heading">
          <h2 id="auto-voice-title">Automatic voice rooms</h2>
          <p>Configure rooms created from the public voice trigger.</p>
        </div>
        <div className="form-grid">
          <Field label="Trigger channel" error={inputError('auto_voice_trigger')}><input {...form.register('auto_voice_trigger')} /></Field>
          <Field label="Room suffix" error={inputError('auto_voice_suffix')}><input {...form.register('auto_voice_suffix')} /></Field>
          <Field label="Default user limit" hint="0 allows unlimited members; maximum 99." error={inputError('auto_voice_limit')}><input type="number" min="0" max="99" {...form.register('auto_voice_limit')} /></Field>
        </div>
      </section>

      <section className="settings-section" aria-labelledby="private-title">
        <div className="section-heading"><h2 id="private-title">Private rooms</h2><p>Control password-protected room creation.</p></div>
        <div className="form-grid">
          <Field label="Category" error={inputError('private_category')}><input {...form.register('private_category')} /></Field>
          <Field label="Trigger channel" error={inputError('private_trigger')}><input {...form.register('private_trigger')} /></Field>
          <Field label="Room suffix" error={inputError('private_suffix')}><input {...form.register('private_suffix')} /></Field>
          <Field label="Default user limit" error={inputError('private_limit')}><input type="number" min="0" max="99" {...form.register('private_limit')} /></Field>
          <Field label="Password channel" error={inputError('password_channel')}><input {...form.register('password_channel')} /></Field>
        </div>
      </section>

      <section className="settings-section" aria-labelledby="skills-title">
        <div className="section-heading"><h2 id="skills-title">Skill panel</h2><p>Set command behavior and direct-join skills.</p></div>
        <div className="form-grid">
          <Field label="Command prefix" error={inputError('skill_prefix')}><input {...form.register('skill_prefix')} /></Field>
          <Field label="Panel channel" error={inputError('skill_panel_channel')}><input {...form.register('skill_panel_channel')} /></Field>
          <Field label="Direct-join skills" hint="One unique skill name per line." error={inputError('skill_panel_direct_join_skills')}><textarea rows={5} {...form.register('skill_panel_direct_join_skills')} /></Field>
        </div>
      </section>

      <section className="settings-section" aria-labelledby="leveling-title">
        <div className="section-heading"><h2 id="leveling-title">Leveling</h2><p>Tune XP awards, timing, and progression roles.</p></div>
        <div className="form-grid compact-grid">
          <Field label="Message XP minimum" error={inputError('xp_per_message_min')}><input type="number" min="0" {...form.register('xp_per_message_min')} /></Field>
          <Field label="Message XP maximum" error={inputError('xp_per_message_max')}><input type="number" min="0" {...form.register('xp_per_message_max')} /></Field>
          <Field label="Message cooldown (seconds)" error={inputError('xp_message_cooldown')}><input type="number" min="0" {...form.register('xp_message_cooldown')} /></Field>
          <Field label="Voice XP per tick" error={inputError('xp_per_voice_tick')}><input type="number" min="0" {...form.register('xp_per_voice_tick')} /></Field>
          <Field label="Voice interval (seconds)" error={inputError('xp_voice_interval')}><input type="number" min="1" {...form.register('xp_voice_interval')} /></Field>
          <Field label="Daily XP base" error={inputError('xp_daily_base')}><input type="number" min="0" {...form.register('xp_daily_base')} /></Field>
          <Field label="Level-up channel" error={inputError('levelup_channel')}><input {...form.register('levelup_channel')} /></Field>
          <Field label="Level roles" hint={'JSON rows: [level, "role name", decimal color].'} error={inputError('level_roles')}><textarea className="code-input" rows={8} spellCheck="false" {...form.register('level_roles')} /></Field>
        </div>
      </section>

      <div className="save-bar">
        <div className="save-status" aria-live="polite">
          {mutation.isError && <span className="save-error">{mutation.error.message}</span>}
          {mutation.isSuccess && !form.formState.isDirty && <span className="save-success"><Check aria-hidden="true" /> Settings saved</span>}
          {form.formState.isDirty && <span>Unsaved changes</span>}
        </div>
        <button className="button primary" type="submit" disabled={mutation.isPending || !form.formState.isDirty}>
          <Save aria-hidden="true" /> {mutation.isPending ? 'Saving...' : 'Save settings'}
        </button>
      </div>
    </form>
  )
}

export function SettingsPage() {
  const { guildId } = useParams({ from: '/authenticated/guilds/$guildId/settings' })
  const guilds = useQuery({ queryKey: ['guilds'], queryFn: getGuilds })
  const guild = guilds.data?.find((item) => item.id === guildId)

  return (
    <main className="page">
      <Link className="back-link" to="/guilds"><ArrowLeft aria-hidden="true" /> All servers</Link>
      <div className="page-heading settings-heading">
        <div><p className="eyebrow">Server settings</p><h1>{guild?.name ?? 'Discord server'}</h1><p>Changes affect this server only.</p></div>
        <div className="heading-icon"><Settings2 aria-hidden="true" /></div>
      </div>
      <SettingsForm guildId={guildId} />
    </main>
  )
}