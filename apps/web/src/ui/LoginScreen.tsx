import { Bot, LogIn, ShieldCheck } from 'lucide-react'

export function LoginScreen() {
  return (
    <main className="login-page">
      <section className="login-panel" aria-labelledby="login-title">
        <div className="brand-mark"><Bot aria-hidden="true" /></div>
        <p className="eyebrow">Channel Bot Console</p>
        <h1 id="login-title">Manage your Discord servers</h1>
        <p className="login-copy">
          Sign in with Discord to configure voice rooms, skills, and leveling for servers you manage.
        </p>
        <a className="button primary login-button" href="/api/auth/login">
          <LogIn aria-hidden="true" /> Continue with Discord
        </a>
        <p className="privacy-note"><ShieldCheck aria-hidden="true" /> Authentication stays in a secure server session.</p>
      </section>
    </main>
  )
}