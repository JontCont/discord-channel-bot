import {
  Navigate,
  Outlet,
  createRootRoute,
  createRoute,
  createRouter,
} from '@tanstack/react-router'
import { AuthenticatedLayout } from './ui/AuthenticatedLayout'
import { GuildPicker } from './ui/GuildPicker'
import { PrivacyPolicyPage, TermsOfServicePage } from './ui/LegalPages'
import { LoginScreen } from './ui/LoginScreen'
import { SettingsPage } from './ui/SettingsPage'
import { NotFound } from './ui/States'

const rootRoute = createRootRoute({
  component: Outlet,
  notFoundComponent: NotFound,
})

const indexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/',
  component: () => <Navigate to="/guilds" replace />,
})

const loginRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/login',
  component: LoginScreen,
})

const privacyRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/privacy',
  component: PrivacyPolicyPage,
})

const termsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/terms',
  component: TermsOfServicePage,
})

const authenticatedRoute = createRoute({
  getParentRoute: () => rootRoute,
  id: 'authenticated',
  component: AuthenticatedLayout,
})

const guildsRoute = createRoute({
  getParentRoute: () => authenticatedRoute,
  path: '/guilds',
  component: GuildPicker,
})

const settingsRoute = createRoute({
  getParentRoute: () => authenticatedRoute,
  path: '/guilds/$guildId/settings',
  component: SettingsPage,
})

const routeTree = rootRoute.addChildren([
  indexRoute,
  loginRoute,
  privacyRoute,
  termsRoute,
  authenticatedRoute.addChildren([guildsRoute, settingsRoute]),
])

export const router = createRouter({ routeTree })

declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router
  }
}