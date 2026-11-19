import { Link } from '@tanstack/react-router'
import {
  ArrowRight,
  Bot,
  CheckCircle2,
  Command,
  Hash,
  LayoutDashboard,
  Lock,
  LogIn,
  Megaphone,
  Sliders,
  Sparkles,
  Tag,
  Trophy,
  UserPlus,
  Users,
  Volume2,
} from 'lucide-react'
import { useState, type ComponentType } from 'react'
import { useTranslation } from 'react-i18next'
import { MOCK_GUILD_ID } from '../mock-constants'
import { DisplayControls } from './DisplayControls'

type FeatureKey = 'voice' | 'party' | 'skills' | 'leveling' | 'intro' | 'console'
type CommandGroupKey = 'general' | 'voice' | 'party' | 'skills' | 'leveling'

interface FeatureCardMeta {
  key: FeatureKey
  icon: ComponentType<{ 'aria-hidden'?: boolean | 'true' | 'false' }>
  accent: 'indigo' | 'teal' | 'amber' | 'rose' | 'violet' | 'sky'
  commandSample: string
}

const FEATURE_CARDS: FeatureCardMeta[] = [
  { key: 'voice', icon: Volume2, accent: 'indigo', commandSample: '/setup-voice · /setup-private' },
  { key: 'party', icon: Users, accent: 'teal', commandSample: '/party setup · /party create' },
  { key: 'skills', icon: Tag, accent: 'violet', commandSample: '/skill create · /skill panel' },
  { key: 'leveling', icon: Trophy, accent: 'amber', commandSample: '/daily · /rank · /leaderboard' },
  { key: 'intro', icon: UserPlus, accent: 'rose', commandSample: '/setup-introduction' },
  { key: 'console', icon: LayoutDashboard, accent: 'sky', commandSample: 'OAuth2 · Live Sync' },
]

const COMMAND_GROUPS: Record<CommandGroupKey, Array<{ usage: string; descKey: string }>> = {
  voice: [
    { usage: '/setup-voice', descKey: 'settings.slash.commands.setup_voice' },
    { usage: '/voice-name <name>', descKey: 'settings.slash.commands.voice_name' },
    { usage: '/voice-limit <count>', descKey: 'settings.slash.commands.voice_limit' },
    { usage: '/voice-kick <user>', descKey: 'settings.slash.commands.voice_kick' },
    { usage: '/setup-private', descKey: 'settings.slash.commands.setup_private' },
    { usage: '/voice-invite <user>', descKey: 'settings.slash.commands.voice_invite' },
    { usage: '/fix-private-perms', descKey: 'settings.slash.commands.fix_private_perms' },
  ],
  party: [
    { usage: '/party setup', descKey: 'settings.slash.commands.party_setup' },
    { usage: '/party create', descKey: 'settings.slash.commands.party_create' },
    { usage: '/party list', descKey: 'settings.slash.commands.party_list' },
  ],
  skills: [
    { usage: '/skill create <name> [emoji]', descKey: 'settings.slash.commands.skill_create' },
    { usage: '/skill panel', descKey: 'settings.slash.commands.skill_panel' },
    { usage: '/skill join <code>', descKey: 'settings.slash.commands.skill_join' },
    { usage: '/skill leave <name>', descKey: 'settings.slash.commands.skill_leave' },
    { usage: '/skill info <name>', descKey: 'settings.slash.commands.skill_info' },
    { usage: '/skill regen <name>', descKey: 'settings.slash.commands.skill_regen' },
    { usage: '/skill list', descKey: 'settings.slash.commands.skill_list' },
    { usage: '/skill setup', descKey: 'settings.slash.commands.skill_setup' },
  ],
  leveling: [
    { usage: '/daily', descKey: 'settings.slash.commands.daily' },
    { usage: '/rank [user]', descKey: 'settings.slash.commands.rank' },
    { usage: '/leaderboard', descKey: 'settings.slash.commands.leaderboard' },
    { usage: '/level-init', descKey: 'settings.slash.commands.level_init' },
    { usage: '/level-preview', descKey: 'settings.slash.commands.level_preview' },
  ],
  general: [
    { usage: '/help [category]', descKey: 'settings.slash.commands.help' },
    { usage: '/userinfo [user]', descKey: 'settings.slash.commands.userinfo' },
    { usage: '/announce <title> <content>', descKey: 'settings.slash.commands.announce' },
  ],
}

export function HomePage() {
  const { t } = useTranslation()
  const [activeCommandGroup, setActiveCommandGroup] = useState<CommandGroupKey>('voice')
  const isMock = import.meta.env.VITE_MOCK === 'true'

  return (
    <div className="home-shell">
      <div className="home-ambient" aria-hidden="true">
        <span className="home-orb orb-primary" />
        <span className="home-orb orb-teal" />
        <span className="home-orb orb-violet" />
        <span className="home-grid-backdrop" />
      </div>

      <header className="home-navbar">
        <div className="home-navbar-inner">
          <Link className="brand home-brand" to="/" aria-label={t('common.productHome')}>
            <span className="brand-mark small home-brand-mark">
              <Bot aria-hidden="true" />
            </span>
            <span>Channel Bot</span>
          </Link>

          <nav className="home-nav-links" aria-label="Primary navigation">
            <a href="#features">{t('home.nav.features')}</a>
            <a href="#workflow">{t('home.nav.workflow')}</a>
            <a href="#commands">{t('home.nav.commands')}</a>
          </nav>

          <div className="home-nav-actions">
            <DisplayControls />
            {isMock ? (
              <Link
                className="button primary home-nav-cta"
                to="/guilds/$guildId/settings"
                params={{ guildId: MOCK_GUILD_ID }}
              >
                <LayoutDashboard aria-hidden="true" />
                <span>{t('home.hero.mockCta')}</span>
              </Link>
            ) : (
              <Link className="button primary home-nav-cta" to="/guilds">
                <LayoutDashboard aria-hidden="true" />
                <span>{t('home.nav.console')}</span>
              </Link>
            )}
          </div>
        </div>
      </header>

      <main className="home-main">
        {/* Hero Section */}
        <section className="home-hero">
          <div className="home-hero-copy">
            <div className="home-status-pill">
              <span className="home-status-dot" aria-hidden="true" />
              <Sparkles aria-hidden="true" />
              <span>{t('home.hero.badge')}</span>
            </div>

            <h1 className="home-hero-title">
              <span>{t('home.hero.titleLead')}</span>{' '}
              <span className="home-gradient-text">{t('home.hero.titleAccent')}</span>
            </h1>

            <p className="home-hero-subtitle">{t('home.hero.subtitle')}</p>

            <div className="home-hero-actions">
              {isMock ? (
                <Link
                  className="button primary home-cta-primary"
                  to="/guilds/$guildId/settings"
                  params={{ guildId: MOCK_GUILD_ID }}
                >
                  <LayoutDashboard aria-hidden="true" />
                  <span>{t('home.hero.mockCta')}</span>
                  <ArrowRight aria-hidden="true" />
                </Link>
              ) : (
                <Link className="button primary home-cta-primary" to="/guilds">
                  <LayoutDashboard aria-hidden="true" />
                  <span>{t('home.hero.primaryCta')}</span>
                  <ArrowRight aria-hidden="true" />
                </Link>
              )}

              <a className="button secondary home-cta-secondary" href="/api/bot/invite">
                <Bot aria-hidden="true" />
                <span>{t('home.hero.secondaryCta')}</span>
              </a>

              <a className="home-cta-textlink" href="#features">
                <span>{t('home.hero.exploreCta')}</span>
                <ArrowRight aria-hidden="true" />
              </a>
            </div>

            <div className="home-live-indicator">
              <span className="pulse-ring" aria-hidden="true" />
              <span>{t('home.hero.liveStatus')}</span>
            </div>
          </div>

          {/* Animated Interactive Discord & Console Preview Mockup */}
          <div className="home-hero-visual" aria-hidden="true">
            <div className="home-preview-window">
              <div className="home-preview-titlebar">
                <div className="window-dots">
                  <span className="dot-red" />
                  <span className="dot-yellow" />
                  <span className="dot-green" />
                </div>
                <span className="window-title">{t('home.preview.serverName')}</span>
                <span className="window-tag">v2.7+</span>
              </div>

              <div className="home-preview-body">
                <aside className="home-preview-channels">
                  <div className="preview-ch-item active">
                    <Hash />
                    <span>{t('home.preview.channelHub')}</span>
                  </div>
                  <div className="preview-ch-item">
                    <Megaphone />
                    <span>{t('home.preview.channelParty')}</span>
                  </div>
                  <div className="preview-ch-item voice">
                    <Volume2 />
                    <span>{t('home.preview.channelVoice')}</span>
                  </div>
                  <div className="preview-ch-item private">
                    <Lock />
                    <span>{t('home.preview.channelPrivate')}</span>
                  </div>
                  <div className="preview-voice-wave">
                    <span />
                    <span />
                    <span />
                    <span />
                    <span />
                  </div>
                </aside>

                <div className="home-preview-stage">
                  <div className="preview-embed-card">
                    <div className="preview-embed-badge">{t('home.preview.panelTag')}</div>
                    <h3>{t('home.preview.panelTitle')}</h3>
                    <p>{t('home.preview.panelDesc')}</p>
                    <div className="preview-skill-chips">
                      <span className="preview-chip">🎮 Gaming · 28</span>
                      <span className="preview-chip">⚒️ Crafting · 14</span>
                      <span className="preview-chip">🎨 Art · 9</span>
                    </div>
                    <div className="preview-embed-buttons">
                      <span className="preview-btn primary">{t('home.preview.btnCreate')}</span>
                      <span className="preview-btn">{t('home.preview.btnJoin')}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div className="home-float-card float-sync">
              <div className="float-icon teal">
                <Sliders />
              </div>
              <div>
                <strong>{t('home.preview.toastTitle')}</strong>
                <p>{t('home.preview.toastDesc')}</p>
              </div>
            </div>

            <div className="home-float-card float-xp">
              <div className="float-icon amber">
                <Trophy />
              </div>
              <span>{t('home.preview.xpBadge')}</span>
            </div>
          </div>
        </section>

        {/* Stats Bar */}
        <section className="home-stats-bar" aria-label="Key capabilities">
          <div className="home-stat-card">
            <strong>{t('home.stats.modulesValue')}</strong>
            <span>{t('home.stats.modulesLabel')}</span>
          </div>
          <div className="home-stat-card">
            <strong>{t('home.stats.commandsValue')}</strong>
            <span>{t('home.stats.commandsLabel')}</span>
          </div>
          <div className="home-stat-card">
            <strong>{t('home.stats.tiersValue')}</strong>
            <span>{t('home.stats.tiersLabel')}</span>
          </div>
          <div className="home-stat-card">
            <strong>{t('home.stats.syncValue')}</strong>
            <span>{t('home.stats.syncLabel')}</span>
          </div>
        </section>

        {/* Feature Bento Grid */}
        <section id="features" className="home-section">
          <div className="home-section-header">
            <p className="eyebrow">{t('home.features.eyebrow')}</p>
            <h2>{t('home.features.title')}</h2>
            <p>{t('home.features.description')}</p>
          </div>

          <div className="home-features-grid">
            {FEATURE_CARDS.map((card, index) => {
              const Icon = card.icon
              const bullets = t(`home.features.items.${card.key}.bullets`, {
                returnObjects: true,
              }) as string[]

              return (
                <article
                  key={card.key}
                  className={`home-feature-card accent-${card.accent}`}
                  style={{ animationDelay: `${index * 90}ms` }}
                >
                  <div className="feature-card-top">
                    <div className={`feature-icon-box accent-${card.accent}`}>
                      <Icon aria-hidden="true" />
                    </div>
                    <span className="feature-tag-pill">
                      {t(`home.features.items.${card.key}.tag`)}
                    </span>
                  </div>

                  <h3>{t(`home.features.items.${card.key}.title`)}</h3>
                  <p className="feature-card-desc">
                    {t(`home.features.items.${card.key}.description`)}
                  </p>

                  <ul className="feature-bullet-list">
                    {Array.isArray(bullets) &&
                      bullets.map((bullet) => (
                        <li key={bullet}>
                          <CheckCircle2 aria-hidden="true" />
                          <span>{bullet}</span>
                        </li>
                      ))}
                  </ul>

                  <div className="feature-card-footer">
                    <code>{card.commandSample}</code>
                  </div>
                </article>
              )
            })}
          </div>
        </section>

        {/* Workflow Section */}
        <section id="workflow" className="home-section home-workflow-section">
          <div className="home-section-header">
            <p className="eyebrow">{t('home.workflow.eyebrow')}</p>
            <h2>{t('home.workflow.title')}</h2>
            <p>{t('home.workflow.description')}</p>
          </div>

          <div className="home-workflow-steps">
            <div className="workflow-step-card">
              <div className="workflow-step-number">01</div>
              <h3>{t('home.workflow.step1Title')}</h3>
              <p>{t('home.workflow.step1Desc')}</p>
            </div>
            <div className="workflow-step-card">
              <div className="workflow-step-number">02</div>
              <h3>{t('home.workflow.step2Title')}</h3>
              <p>{t('home.workflow.step2Desc')}</p>
            </div>
            <div className="workflow-step-card">
              <div className="workflow-step-number">03</div>
              <h3>{t('home.workflow.step3Title')}</h3>
              <p>{t('home.workflow.step3Desc')}</p>
            </div>
          </div>
        </section>

        {/* Interactive Slash Commands Showcase */}
        <section id="commands" className="home-section">
          <div className="home-section-header">
            <p className="eyebrow">{t('home.commands.eyebrow')}</p>
            <h2>{t('home.commands.title')}</h2>
            <p>{t('home.commands.description')}</p>
          </div>

          <div className="home-commands-Explorer">
            <div className="home-commands-tabs" role="tablist" aria-label={t('home.commands.title')}>
              {(['voice', 'party', 'skills', 'leveling', 'general'] as CommandGroupKey[]).map(
                (groupKey) => (
                  <button
                    key={groupKey}
                    type="button"
                    role="tab"
                    aria-selected={activeCommandGroup === groupKey}
                    className={`home-command-tab ${activeCommandGroup === groupKey ? 'active' : ''}`}
                    onClick={() => setActiveCommandGroup(groupKey)}
                  >
                    <Command aria-hidden="true" />
                    <span>{t(`settings.slash.groups.${groupKey}`)}</span>
                  </button>
                ),
              )}
            </div>

            <div className="home-commands-list" role="tabpanel">
              {COMMAND_GROUPS[activeCommandGroup].map((cmd) => (
                <div key={cmd.usage} className="home-command-row">
                  <code className="home-command-code">{cmd.usage}</code>
                  <span className="home-command-desc">{t(cmd.descKey)}</span>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Bottom CTA Banner */}
        <section className="home-cta-banner">
          <div className="home-cta-banner-content">
            <h2>{t('home.cta.title')}</h2>
            <p>{t('home.cta.description')}</p>
          </div>
          <div className="home-cta-banner-actions">
            {isMock ? (
              <Link
                className="button primary home-cta-primary"
                to="/guilds/$guildId/settings"
                params={{ guildId: MOCK_GUILD_ID }}
              >
                <LayoutDashboard aria-hidden="true" />
                <span>{t('home.hero.mockCta')}</span>
              </Link>
            ) : (
              <>
                <Link className="button primary home-cta-primary" to="/guilds">
                  <LayoutDashboard aria-hidden="true" />
                  <span>{t('home.cta.primary')}</span>
                </Link>
                <a className="button secondary home-cta-secondary" href="/api/auth/login">
                  <LogIn aria-hidden="true" />
                  <span>{t('home.cta.secondary')}</span>
                </a>
              </>
            )}
          </div>
        </section>
      </main>

      <footer className="home-footer">
        <div className="home-footer-inner">
          <div className="home-footer-brand">
            <Link className="brand" to="/">
              <span className="brand-mark small">
                <Bot aria-hidden="true" />
              </span>
              <span>Channel Bot</span>
            </Link>
            <p>{t('home.footer.tagline')}</p>
          </div>

          <nav className="home-footer-links" aria-label={t('login.legalLabel')}>
            <Link to="/">{t('home.footer.home')}</Link>
            <Link to="/guilds">{t('home.footer.console')}</Link>
            <Link to="/login">{t('home.nav.signIn')}</Link>
            <Link to="/privacy">{t('login.privacy')}</Link>
            <Link to="/terms">{t('login.terms')}</Link>
          </nav>
        </div>
      </footer>
    </div>
  )
}
