import { Link } from '@tanstack/react-router'
import { Bot } from 'lucide-react'
import type { ReactNode } from 'react'

const EFFECTIVE_DATE = 'September 1, 2026'

function LegalPage({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="legal-shell">
      <header className="legal-topbar">
        <Link className="brand" to="/login" aria-label="Channel Bot home">
          <span className="brand-mark small"><Bot aria-hidden="true" /></span>
          <span>Channel Bot</span>
        </Link>
        <nav className="legal-nav" aria-label="Legal pages">
          <Link to="/privacy" activeProps={{ 'aria-current': 'page' }}>Privacy</Link>
          <Link to="/terms" activeProps={{ 'aria-current': 'page' }}>Terms</Link>
        </nav>
      </header>
      <main className="legal-page">
        <p className="eyebrow">Channel Bot</p>
        <h1>{title}</h1>
        <p className="legal-date">Effective date: {EFFECTIVE_DATE}</p>
        <div className="legal-content">{children}</div>
      </main>
    </div>
  )
}

export function PrivacyPolicyPage() {
  return (
    <LegalPage title="Privacy Policy">
      <section>
        <h2>1. Overview</h2>
        <p>
          This policy explains how Channel Bot collects, uses, and stores information when you use
          the Discord bot or its management console (the “Service”).
        </p>
      </section>
      <section>
        <h2>2. Information we process</h2>
        <ul>
          <li><strong>Discord account data:</strong> your user ID, username, display name, and avatar.</li>
          <li><strong>Server data:</strong> server IDs, names, icons, and your server-management permissions.</li>
          <li><strong>Bot activity data:</strong> user and server IDs, XP, level, message reward timestamp, daily streak, and last check-in date.</li>
          <li><strong>Configuration data:</strong> server settings and generated skill invite codes.</li>
          <li><strong>Authentication data:</strong> a Discord OAuth access token and a random session identifier while your session is active.</li>
        </ul>
        <p>Channel Bot does not store the content of your Discord messages.</p>
      </section>
      <section>
        <h2>3. How we use information</h2>
        <p>
          We use this information only to authenticate administrators, show manageable servers,
          operate configured bot features, maintain leveling and check-in progress, and protect the Service.
        </p>
      </section>
      <section>
        <h2>4. Sharing and third parties</h2>
        <p>
          We do not sell personal information. Information is shared with Discord only as needed to
          authenticate you and provide bot functionality. Discord processes information under its own privacy policy.
        </p>
      </section>
      <section>
        <h2>5. Storage and retention</h2>
        <p>
          Login sessions and OAuth tokens are kept in server memory for up to eight hours and are
          removed when they expire, when you sign out, or when the Service restarts. Server settings,
          skill invite codes, and leveling records remain until they are deleted or the Service is discontinued.
        </p>
      </section>
      <section>
        <h2>6. Security</h2>
        <p>
          We use restricted OAuth scopes, HTTP-only same-site cookies, permission checks, and other
          reasonable safeguards. No method of storage or transmission is completely secure.
        </p>
      </section>
      <section>
        <h2>7. Your choices</h2>
        <p>
          You may sign out to end your web session and remove the bot from a server to stop future
          bot activity there. To request access to or deletion of stored information, contact the
          operator who made Channel Bot available to your Discord server.
        </p>
      </section>
      <section>
        <h2>8. Changes</h2>
        <p>We may update this policy. The effective date above will be revised when changes are published.</p>
      </section>
    </LegalPage>
  )
}

export function TermsOfServicePage() {
  return (
    <LegalPage title="Terms of Service">
      <section>
        <h2>1. Acceptance</h2>
        <p>
          By inviting, accessing, or using Channel Bot or its management console (the “Service”),
          you agree to these terms and to Discord’s applicable terms and community guidelines.
        </p>
      </section>
      <section>
        <h2>2. Eligibility and authority</h2>
        <p>
          You must be permitted to use Discord and have authority to install or configure the Service
          for the relevant server. The console may restrict settings to members with server-management permissions.
        </p>
      </section>
      <section>
        <h2>3. Acceptable use</h2>
        <p>You agree not to:</p>
        <ul>
          <li>use the Service for unlawful, abusive, deceptive, or harassing activity;</li>
          <li>attempt to bypass permissions, access another server’s data, or compromise the Service;</li>
          <li>interfere with availability, overload the Service, or automate requests in a harmful way; or</li>
          <li>use the Service in a way that violates Discord’s terms or the rights of others.</li>
        </ul>
      </section>
      <section>
        <h2>4. Your configuration and conduct</h2>
        <p>
          Server administrators are responsible for settings they choose, permissions they grant,
          generated channels and roles, and how members use those features. Keep skill invite codes confidential where appropriate.
        </p>
      </section>
      <section>
        <h2>5. Availability and changes</h2>
        <p>
          The Service is provided on an “as is” and “as available” basis. Features may be changed,
          suspended, or discontinued without notice. We do not guarantee uninterrupted or error-free operation.
        </p>
      </section>
      <section>
        <h2>6. Suspension and termination</h2>
        <p>
          Access may be limited or terminated when these terms are violated, when required to protect
          users or the Service, or when Discord access is revoked. You may stop using the Service at any time.
        </p>
      </section>
      <section>
        <h2>7. Disclaimers and liability</h2>
        <p>
          To the extent permitted by law, the Service operator disclaims implied warranties and is not
          liable for indirect, incidental, special, consequential, or punitive damages, or for lost data,
          profits, or access resulting from use of the Service.
        </p>
      </section>
      <section>
        <h2>8. Privacy and changes</h2>
        <p>
          Our <Link to="/privacy">Privacy Policy</Link> explains how information is handled. We may update
          these terms; continued use after an update means you accept the revised terms.
        </p>
      </section>
      <section>
        <h2>9. Contact</h2>
        <p>Questions about these terms may be directed to the operator who made Channel Bot available to your Discord server.</p>
      </section>
    </LegalPage>
  )
}